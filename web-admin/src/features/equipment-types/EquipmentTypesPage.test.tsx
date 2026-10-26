import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EquipmentTypesPage } from "./EquipmentTypesPage";
import type { EquipmentType } from "./types";

const SPLIT: EquipmentType = { id: "et1", name: "Split", is_active: true };
const CAMARA: EquipmentType = { id: "et2", name: "Cámara frigorífica", is_active: false };

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

/** Simula la API del catálogo y registra cada llamada. */
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
      const includeInactive = call.query.includes("include_inactive=true");
      return json(includeInactive ? [CAMARA, SPLIT] : [SPLIT]);
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
      <EquipmentTypesPage />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe("EquipmentTypesPage", () => {
  it("lista los tipos activos y muestra los desactivados al pedirlo", async () => {
    stubApi();
    renderPage();

    expect(await screen.findByText("Split")).toBeInTheDocument();
    expect(screen.queryByText("Cámara frigorífica")).not.toBeInTheDocument();

    await userEvent.click(screen.getByLabelText("Mostrar desactivados"));

    expect(await screen.findByText("Cámara frigorífica")).toBeInTheDocument();
    expect(screen.getByText("Desactivado")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Reactivar Cámara frigorífica" }),
    ).toBeInTheDocument();
  });

  it("avisa cuando todavía no hay tipos cargados", async () => {
    stubApi(() => json([]));
    renderPage();

    expect(await screen.findByText("Todavía no hay tipos de equipo.")).toBeInTheDocument();
  });

  it("crea un tipo de equipo", async () => {
    const calls = stubApi((call) =>
      call.method === "POST"
        ? json({ id: "et3", name: "Heladera comercial", is_active: true }, 201)
        : undefined,
    );
    renderPage();
    await screen.findByText("Split");

    await userEvent.type(screen.getByLabelText("Nuevo tipo de equipo"), "Heladera comercial");
    await userEvent.click(screen.getByRole("button", { name: "Agregar tipo" }));

    await waitFor(() =>
      expect(calls).toContainEqual(
        expect.objectContaining({
          method: "POST",
          path: "/api/admin/equipment-types",
          body: { name: "Heladera comercial" },
        }),
      ),
    );
  });

  it("muestra un error claro si el nombre ya existe", async () => {
    stubApi((call) =>
      call.method === "POST"
        ? json({ detail: { code: "equipment_type_name_already_exists", message: "x" } }, 409)
        : undefined,
    );
    renderPage();
    await screen.findByText("Split");

    await userEvent.type(screen.getByLabelText("Nuevo tipo de equipo"), "split");
    await userEvent.click(screen.getByRole("button", { name: "Agregar tipo" }));

    expect(
      await screen.findByText(
        "Ya existe un tipo de equipo con ese nombre (puede estar desactivado).",
      ),
    ).toBeInTheDocument();
  });

  it("renombra y desactiva un tipo de equipo", async () => {
    const calls = stubApi((call) =>
      call.method === "PATCH" ? json({ ...SPLIT, ...(call.body as object) }) : undefined,
    );
    renderPage();
    await screen.findByText("Split");

    await userEvent.click(screen.getByRole("button", { name: "Renombrar Split" }));
    const input = screen.getByLabelText("Nombre nuevo");
    await userEvent.clear(input);
    await userEvent.type(input, "Split inverter");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await userEvent.click(await screen.findByRole("button", { name: "Desactivar Split" }));

    await waitFor(() => {
      const patches = calls.filter((call) => call.method === "PATCH");
      expect(patches.map((call) => call.body)).toEqual([
        { name: "Split inverter" },
        { is_active: false },
      ]);
      expect(patches[0].path).toBe("/api/admin/equipment-types/et1");
    });
  });
});
