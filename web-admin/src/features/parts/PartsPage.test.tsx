import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PartsPage } from "./PartsPage";
import type { Part } from "./types";

const GAS: Part = {
  id: "p1",
  name: "Gas R410A",
  unit: "kg",
  is_active: true,
  list_price: "0.00",
  price_updated_at: "2026-11-02T13:00:00Z",
};
const CANO: Part = {
  id: "p2",
  name: "Caño de cobre 1/4",
  unit: "metro",
  is_active: true,
  list_price: "1500.50",
  price_updated_at: "2026-11-02T13:00:00Z",
};
const VIEJO: Part = { ...GAS, id: "p3", name: "Filtro viejo", is_active: false };

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

interface Call {
  method: string;
  path: string;
  query: string;
  body: unknown;
}

function stubApi(handler?: (call: Call) => Response | undefined) {
  const calls: Call[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (request: Request) => {
      const url = new URL(request.url);
      const body = request.method === "GET" ? null : await request.clone().json();
      const call = { method: request.method, path: url.pathname, query: url.search, body };
      calls.push(call);
      const custom = handler?.(call);
      if (custom) {
        return custom;
      }
      if (call.method === "GET") {
        const all = call.query.includes("include_inactive=true");
        return json(all ? [CANO, VIEJO, GAS] : [CANO, GAS]);
      }
      return json({ ...GAS, ...(call.body as object) });
    }),
  );
  return calls;
}

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <PartsPage />
    </QueryClientProvider>,
  );
}

function row(name: string) {
  return screen.getByRole("row", { name: new RegExp(name) });
}

afterEach(() => vi.restoreAllMocks());

describe("PartsPage", () => {
  it("lista los materiales con unidad y precio en pesos", async () => {
    stubApi();
    renderPage();

    await screen.findByText("Gas R410A");
    expect(within(row("Gas R410A")).getByText("kg")).toBeInTheDocument();
    expect(within(row("Caño de cobre")).getByLabelText("Precio de Caño de cobre 1/4")).toHaveValue(
      "1500,50",
    );
    expect(screen.queryByText("Filtro viejo")).not.toBeInTheDocument();
  });

  it("guarda un precio nuevo escrito con coma", async () => {
    const calls = stubApi();
    renderPage();
    const user = userEvent.setup();

    const precio = await screen.findByLabelText("Precio de Gas R410A");
    await user.clear(precio);
    await user.type(precio, "1800,5");
    await user.click(within(row("Gas R410A")).getByRole("button", { name: "Guardar precio" }));

    await waitFor(() =>
      expect(calls).toContainEqual(
        expect.objectContaining({
          method: "PUT",
          path: "/api/admin/parts/p1/price",
          body: { list_price: "1800.5" },
        }),
      ),
    );
    expect(await within(row("Gas R410A")).findByText("Precio guardado.")).toBeInTheDocument();
  });

  it("no manda un precio inválido", async () => {
    const calls = stubApi();
    renderPage();
    const user = userEvent.setup();

    const precio = await screen.findByLabelText("Precio de Gas R410A");
    await user.clear(precio);
    await user.type(precio, "12,345");
    await user.click(within(row("Gas R410A")).getByRole("button", { name: "Guardar precio" }));

    expect(await screen.findByText(/solo números, con hasta dos decimales/)).toBeInTheDocument();
    expect(calls.some((c) => c.method === "PUT")).toBe(false);
  });

  it("da de alta un material con su unidad y avisa si hay uno parecido", async () => {
    const calls = stubApi();
    renderPage();
    const user = userEvent.setup();

    await screen.findByText("Gas R410A");
    await user.type(screen.getByLabelText("Nuevo material"), "Cano de cobre");
    expect(screen.getByText(/Ya hay uno parecido: Caño de cobre 1\/4/)).toBeInTheDocument();
    await user.type(screen.getByLabelText("Unidad"), "metro");
    await user.click(screen.getByRole("button", { name: "Agregar material" }));

    await waitFor(() =>
      expect(calls).toContainEqual(
        expect.objectContaining({
          method: "POST",
          path: "/api/admin/parts",
          body: { name: "Cano de cobre", unit: "metro" },
        }),
      ),
    );
  });

  it("muestra el mensaje del nombre repetido", async () => {
    stubApi((call) =>
      call.method === "POST"
        ? json({ detail: { code: "part_name_already_exists" } }, 409)
        : undefined,
    );
    renderPage();
    const user = userEvent.setup();

    await screen.findByText("Gas R410A");
    await user.type(screen.getByLabelText("Nuevo material"), "Gas R410A");
    await user.click(screen.getByRole("button", { name: "Agregar material" }));

    expect(await screen.findByText(/Ya existe un material con ese nombre/)).toBeInTheDocument();
  });

  it("desactiva un material y muestra los desactivados al pedirlo", async () => {
    const calls = stubApi();
    renderPage();
    const user = userEvent.setup();

    await screen.findByText("Gas R410A");
    await user.click(within(row("Gas R410A")).getByRole("button", { name: "Desactivar" }));
    await waitFor(() =>
      expect(calls).toContainEqual(
        expect.objectContaining({
          method: "PATCH",
          path: "/api/admin/parts/p1",
          body: { is_active: false },
        }),
      ),
    );

    await user.click(screen.getByLabelText("Mostrar desactivados"));
    expect(await screen.findByText("Filtro viejo")).toBeInTheDocument();
  });

  it("filtra por nombre", async () => {
    stubApi();
    renderPage();
    const user = userEvent.setup();

    await screen.findByText("Gas R410A");
    await user.type(screen.getByLabelText("Buscar material"), "caño");

    expect(screen.queryByText("Gas R410A")).not.toBeInTheDocument();
    expect(screen.getByText("Caño de cobre 1/4")).toBeInTheDocument();
  });
});
