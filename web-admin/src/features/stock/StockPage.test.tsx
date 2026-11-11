import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { StockPage } from "./StockPage";
import type { Movement, StockLocation, StockPart } from "./types";

const DEPOSITO: StockLocation = {
  id: "l1",
  kind: "warehouse",
  name: "Depósito central",
  crew_id: null,
  crew_name: null,
  is_active: true,
};
const CAMIONETA: StockLocation = {
  id: "l2",
  kind: "truck",
  name: "Camioneta 1",
  crew_id: "c1",
  crew_name: "Escuadrilla 1",
  is_active: true,
};
const GAS: StockPart = {
  part_id: "p1",
  part_name: "Gas R410A",
  unit: "kg",
  total: "5.500",
  has_negative: true,
  by_location: [
    {
      part_id: "p1",
      part_name: "Gas R410A",
      unit: "kg",
      location_id: "l1",
      location_name: "Depósito central",
      quantity: "6.500",
    },
    {
      part_id: "p1",
      part_name: "Gas R410A",
      unit: "kg",
      location_id: "l2",
      location_name: "Camioneta 1",
      quantity: "-1.000",
    },
  ],
};
const USO: Movement = {
  id: "m1",
  kind: "usage",
  quantity: "2.000",
  from_location_name: "Camioneta 1",
  to_location_name: null,
  work_order_id: "o7",
  work_order_number: 7,
  reason: null,
  created_by_name: "Celular 1",
  occurred_at: "2026-11-10T13:00:00Z",
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function mockApi() {
  const fetchMock = vi.fn(async (request: Request) => {
    const url = new URL(request.url);
    if (url.pathname.endsWith("/admin/stock/locations")) {
      return json([DEPOSITO, CAMIONETA]);
    }
    if (url.pathname.endsWith("/admin/stock")) {
      return json([GAS]);
    }
    if (url.pathname.endsWith("/movements")) {
      return json({ items: [USO], total: 1, limit: 50, offset: 0 });
    }
    if (url.pathname.endsWith("/admin/parts")) {
      return json([{ id: "p1", name: "Gas R410A", unit: "kg", is_active: true }]);
    }
    if (url.pathname.endsWith("/admin/crews")) {
      return json([]);
    }
    if (url.pathname.endsWith("/admin/stock/transfers")) {
      return json(USO, 201);
    }
    return json({}, 404);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderStock() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <StockPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("StockPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  // E08-05 y E08-08: por ubicación y total; el negativo se destaca.
  it("muestra el stock por ubicación y destaca el saldo negativo", async () => {
    mockApi();
    renderStock();

    const tabla = await screen.findByRole("table", { name: "Stock por repuesto" });
    expect(within(tabla).getByText("Saldo negativo: ajustar")).toBeInTheDocument();
    expect(within(tabla).getByText(/Camioneta 1: -1 kg/)).toBeInTheDocument();
    expect(within(tabla).getByText("5,5 kg")).toBeInTheDocument();
  });

  // E08-07: el historial lleva a la orden del uso.
  it("abre el historial con el link a la orden", async () => {
    mockApi();
    renderStock();

    await userEvent.click(await screen.findByRole("button", { name: "Historial de Gas R410A" }));

    const historial = await screen.findByRole("region", { name: "Historial del repuesto" });
    expect(await within(historial).findByRole("link", { name: "Orden N° 7" })).toHaveAttribute(
      "href",
      "/ordenes/o7",
    );
  });

  // E08-03: transferencia entre ubicaciones.
  it("registra una transferencia", async () => {
    const fetchMock = mockApi();
    renderStock();

    await userEvent.click(await screen.findByRole("button", { name: "Transferir" }));
    const form = within(screen.getByRole("form", { name: "Transferir" }));
    await waitFor(() =>
      expect(form.getAllByRole("option", { name: "Gas R410A (kg)" })).toHaveLength(1),
    );
    await userEvent.selectOptions(form.getByLabelText("Repuesto"), "p1");
    await userEvent.selectOptions(form.getByLabelText("Desde"), "l1");
    await userEvent.selectOptions(form.getByLabelText("Hacia"), "l2");
    await userEvent.type(form.getByLabelText("Cantidad"), "1,5");
    await userEvent.click(form.getByRole("button", { name: "Guardar" }));

    await waitFor(() => {
      const posts = fetchMock.mock.calls
        .map(([request]) => request as Request)
        .filter((request) => request.method === "POST");
      expect(posts).toHaveLength(1);
    });
    const [post] = fetchMock.mock.calls
      .map(([request]) => request as Request)
      .filter((request) => request.method === "POST");
    expect(await post.json()).toEqual({
      part_id: "p1",
      from_location_id: "l1",
      to_location_id: "l2",
      quantity: "1.5",
    });
  });
});
