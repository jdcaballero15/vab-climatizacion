import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Part } from "../parts/types";
import { OrderMaterials } from "./OrderMaterials";
import type { OrderMaterials as Materials } from "./types";

const GAS_LINEA = {
  id: "l1",
  part_id: "p1",
  name: "Gas R410A",
  unit: "kg",
  is_other: false,
  quantity: "1.500",
  unit_price: "1000.00",
  subtotal: "1500.00",
  visit_closed_at: "2026-10-28T15:00:00Z",
  added_by_name: "Celular 1",
};
const CANO_LINEA = {
  ...GAS_LINEA,
  id: "l2",
  part_id: "p2",
  name: "Caño de cobre 1/4",
  unit: "metro",
  quantity: "3.200",
  unit_price: "200.00",
  subtotal: "640.00",
  visit_closed_at: "2026-10-30T15:00:00Z",
};
const OTRO_LINEA = {
  ...GAS_LINEA,
  id: "l3",
  part_id: null,
  name: "Cinta aisladora",
  unit: null,
  is_other: true,
  quantity: "2.000",
  unit_price: null,
  subtotal: null,
};
const MATERIALES: Materials = {
  approved: false,
  approved_at: null,
  lines: [GAS_LINEA, CANO_LINEA],
  total: "2140.00",
};
const CAPACITOR: Part = {
  id: "p3",
  name: "Capacitor 35 uF",
  unit: "unidad",
  is_active: true,
  list_price: "300.00",
  price_updated_at: "2026-11-02T13:00:00Z",
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

interface Call {
  method: string;
  path: string;
  body: unknown;
}

function stubApi(
  materials: Materials = MATERIALES,
  handler?: (call: Call) => Response | undefined,
) {
  const calls: Call[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (request: Request) => {
      const url = new URL(request.url);
      const text = request.method === "GET" ? "" : await request.clone().text();
      const body: unknown = text ? JSON.parse(text) : null;
      const call = { method: request.method, path: url.pathname, body };
      calls.push(call);
      const custom = handler?.(call);
      if (custom) {
        return custom;
      }
      if (url.pathname.endsWith("/admin/parts") && request.method === "POST") {
        return json({ ...CAPACITOR, id: "p9", name: "Cinta aisladora" }, 201);
      }
      if (url.pathname.endsWith("/admin/parts")) {
        return json([CAPACITOR]);
      }
      return json(
        materials,
        request.method === "POST" && url.pathname.endsWith("/materials") ? 201 : 200,
      );
    }),
  );
  return calls;
}

function renderMaterials() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <OrderMaterials orderId="o3" orderNumber={3} />
    </QueryClientProvider>,
  );
}

function fila(name: string | RegExp) {
  return screen.getByRole("row", { name });
}

afterEach(() => vi.restoreAllMocks());

describe("OrderMaterials", () => {
  it("muestra cada material con cantidad, precio, subtotal, visita y el total", async () => {
    stubApi();
    renderMaterials();

    const tabla = await screen.findByRole("table", { name: "Materiales de la orden N° 3" });
    const gas = within(tabla).getByRole("row", { name: /Gas R410A/ });
    expect(within(gas).getByLabelText("Cantidad de Gas R410A")).toHaveValue("1,5");
    expect(within(gas).getByText("kg")).toBeInTheDocument();
    expect(within(gas).getByText(/1\.000,00/)).toBeInTheDocument();
    expect(within(gas).getByText(/1\.500,00/)).toBeInTheDocument();
    expect(within(gas).getByText(/28\/10\/2026/)).toBeInTheDocument();
    expect(screen.getByText(/Total materiales/)).toHaveTextContent(/2\.140,00/);
  });

  it("corrige una cantidad escrita con coma", async () => {
    const calls = stubApi();
    renderMaterials();
    const user = userEvent.setup();

    const cantidad = await screen.findByLabelText("Cantidad de Gas R410A");
    await user.clear(cantidad);
    await user.type(cantidad, "2,25");
    await user.click(within(fila(/Gas R410A/)).getByRole("button", { name: "Guardar" }));

    await waitFor(() =>
      expect(calls).toContainEqual({
        method: "PATCH",
        path: "/api/admin/orders/o3/materials/l1",
        body: { quantity: "2.25" },
      }),
    );
  });

  it("no manda una cantidad inválida", async () => {
    const calls = stubApi();
    renderMaterials();
    const user = userEvent.setup();

    const cantidad = await screen.findByLabelText("Cantidad de Gas R410A");
    await user.clear(cantidad);
    await user.type(cantidad, "0");
    await user.click(within(fila(/Gas R410A/)).getByRole("button", { name: "Guardar" }));

    expect(await screen.findByText(/Revisá la cantidad/)).toBeInTheDocument();
    expect(calls.some((c) => c.method === "PATCH")).toBe(false);
  });

  it("saca un material", async () => {
    const calls = stubApi();
    renderMaterials();
    const user = userEvent.setup();

    await screen.findByLabelText("Cantidad de Gas R410A");
    await user.click(within(fila(/Caño de cobre/)).getByRole("button", { name: "Sacar" }));

    await waitFor(() =>
      expect(calls).toContainEqual(
        expect.objectContaining({
          method: "POST",
          path: "/api/admin/orders/o3/materials/l2/removal",
        }),
      ),
    );
  });

  it("agrega un material de la lista", async () => {
    const calls = stubApi();
    renderMaterials();
    const user = userEvent.setup();

    await screen.findByLabelText("Cantidad de Gas R410A");
    await user.selectOptions(await screen.findByLabelText("Material a agregar"), "p3");
    await user.type(screen.getByLabelText("Cantidad a agregar"), "1");
    await user.click(screen.getByRole("button", { name: "Agregar material" }));

    await waitFor(() =>
      expect(calls).toContainEqual({
        method: "POST",
        path: "/api/admin/orders/o3/materials",
        body: { part_id: "p3", quantity: "1" },
      }),
    );
  });

  it("un Otro se ve sin precio y se pasa a la lista con nombre y unidad", async () => {
    const calls = stubApi({ ...MATERIALES, lines: [GAS_LINEA, OTRO_LINEA], total: "1500.00" });
    renderMaterials();
    const user = userEvent.setup();

    await screen.findByLabelText("Cantidad de Gas R410A");
    const otro = fila(/Cinta aisladora/);
    expect(within(otro).getByText("Sin precio")).toBeInTheDocument();
    await user.click(within(otro).getByRole("button", { name: "Pasar a la lista" }));
    const form = screen.getByRole("form", { name: "Pasar Cinta aisladora a la lista" });
    expect(within(form).getByLabelText("Nombre")).toHaveValue("Cinta aisladora");
    await user.type(within(form).getByLabelText("Unidad"), "unidad");
    await user.click(within(form).getByRole("button", { name: "Agregar a la lista" }));

    await waitFor(() =>
      expect(calls).toContainEqual({
        method: "POST",
        path: "/api/admin/orders/o3/materials/l3/promotion",
        body: { part_id: "p9" },
      }),
    );
    expect(calls).toContainEqual({
      method: "POST",
      path: "/api/admin/parts",
      body: { name: "Cinta aisladora", unit: "unidad" },
    });
  });

  it("aprobar muestra el motivo si quedan materiales Otro", async () => {
    stubApi(MATERIALES, (call) =>
      call.path.endsWith("/approval")
        ? json(
            {
              detail: {
                code: "other_materials_pending",
                message: 'Pasá a la lista o sacá los materiales "Otro" antes de aprobar.',
              },
            },
            409,
          )
        : undefined,
    );
    renderMaterials();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Aprobar orden" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/antes de aprobar/);
  });

  it("aprobada queda en solo lectura con la fecha", async () => {
    stubApi({ ...MATERIALES, approved: true, approved_at: "2026-11-02T15:00:00Z" });
    renderMaterials();

    await screen.findByRole("table", { name: "Materiales de la orden N° 3" });
    expect(screen.getByText(/Aprobada el 02\/11\/2026/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Aprobar orden" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sacar" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Cantidad de Gas R410A")).not.toBeInTheDocument();
  });

  it("sin materiales lo dice", async () => {
    stubApi({ approved: false, approved_at: null, lines: [], total: "0.00" });
    renderMaterials();

    expect(await screen.findByText("La escuadrilla no cargó materiales.")).toBeInTheDocument();
  });
});
