import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { OrderDetailPage } from "./OrderDetailPage";
import type { OrderDetail } from "./types";

const DETALLE: OrderDetail = {
  id: "o3",
  number: 3,
  kind: "on_site",
  workshop_stage: null,
  status: "done",
  created_at: "2026-10-20T12:00:00Z",
  client: { id: "c1", number: "10642", name: "Sanatorio Ficticio" },
  site: { label: "Central", address: "Calle 1", reference: "Portón verde" },
  work_type_name: "Reparación",
  equipment: { id: "e1", internal_code: "EA1064201", location_note: "Habitación 12" },
  description: "Pierde agua",
  channel: "whatsapp",
  requester_name: "Marta Ficticia",
  requester_area: "Planta baja",
  assignment: { crew_name: "Escuadrilla 1", scheduled_for: "2026-10-21", return_reason: null },
  cancellation: null,
  has_closure: false,
  source_order: null,
  repair_orders: [],
  timeline: [
    {
      occurred_at: "2026-10-20T12:00:00Z",
      event_type: "created",
      from_status: null,
      to_status: "pending",
      actor_name: "Admin Ficticia",
      note: null,
    },
    {
      occurred_at: "2026-10-21T11:00:00Z",
      event_type: "status_change",
      from_status: "assigned",
      to_status: "in_progress",
      actor_name: "Celular 1",
      note: null,
    },
    {
      occurred_at: "2026-10-21T13:00:00Z",
      event_type: "status_change",
      from_status: "in_progress",
      to_status: "done",
      actor_name: "Celular 1",
      note: "Resuelta.",
    },
    {
      occurred_at: "2026-10-22T15:00:00Z",
      event_type: "status_change",
      from_status: "done",
      to_status: "invoiced",
      actor_name: "Admin Ficticia",
      note: "Factura A-1",
    },
  ],
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function mockApi(detalle: OrderDetail | null) {
  const fetchMock = vi.fn(async (request: Request) => {
    const path = new URL(request.url).pathname;
    if (path.endsWith("/admin/orders/o3")) {
      return detalle ? json(detalle) : json({ detail: { code: "order_not_found" } }, 404);
    }
    if (path.endsWith("/materials")) {
      return json({ approved: false, approved_at: null, lines: [], total: "0.00" });
    }
    if (path.endsWith("/parts")) {
      return json([]);
    }
    return json({}, 404);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderDetail() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/ordenes/o3"]}>
        <Routes>
          <Route path="/ordenes/:orderId" element={<OrderDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("OrderDetailPage", () => {
  // Criterio 1: los datos de la orden.
  it("muestra los datos de la orden", async () => {
    mockApi(DETALLE);
    renderDetail();

    expect(await screen.findByRole("heading", { name: "Orden N° 3" })).toBeInTheDocument();
    const datos = screen.getByLabelText("Datos de la orden N° 3");
    const textos = within(datos)
      .getAllByRole("definition")
      .map((dd) => dd.textContent);
    expect(textos).toEqual([
      "Sanatorio Ficticio (N° 10642)",
      "Central · Calle 1 (Portón verde)",
      "Reparación",
      "EA1064201 · Habitación 12",
      "Escuadrilla 1, prevista para el 21/10/2026",
      "20/10/2026 09:00",
      "WhatsApp",
      "Marta Ficticia · Planta baja",
      "Pierde agua",
    ]);
    expect(screen.getByRole("link", { name: /Órdenes/ })).toHaveAttribute("href", "/ordenes");
  });

  // Criterio 2: cada paso con quién y cuándo.
  it("muestra la línea de tiempo con usuario y fecha", async () => {
    mockApi(DETALLE);
    renderDetail();

    const linea = await screen.findByRole("list", { name: "Línea de tiempo" });
    const pasos = within(linea)
      .getAllByRole("listitem")
      .map((li) => li.textContent);
    expect(pasos).toEqual([
      "20/10/2026 09:00Creada · Admin Ficticia",
      "21/10/2026 08:00Iniciada por la escuadrilla · Celular 1",
      "21/10/2026 10:00Cerrada por la escuadrilla · Celular 1Resuelta.",
      "22/10/2026 12:00Facturada · Admin FicticiaFactura A-1",
    ]);
  });

  it("sin cierre no muestra la sección del cierre", async () => {
    mockApi(DETALLE);
    renderDetail();

    await screen.findByRole("heading", { name: "Orden N° 3" });
    expect(screen.queryByText("Último cierre de la escuadrilla")).not.toBeInTheDocument();
  });

  it("avisa si la orden no existe", async () => {
    mockApi(null);
    renderDetail();

    expect(await screen.findByRole("alert")).toHaveTextContent("No se encontró la orden.");
  });
});
