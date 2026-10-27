import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useParams } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { components } from "../../api/schema";
import { MyOrdersPage } from "./MyOrdersPage";

type CrewOrders = components["schemas"]["CrewOrdersTechnicianOut"];
type Order = components["schemas"]["OrderTechnicianOut"];

const TODAY = "2026-10-26";

function order(overrides: Partial<Order> = {}): Order {
  return {
    id: crypto.randomUUID(),
    number: 2,
    status: "assigned",
    work_type_name: "Reparación",
    description: "Cámara no enfría",
    client_name: "Sanatorio Ficticio",
    scheduled_for: TODAY,
    site: {
      address: "Calle 1",
      reference: "Portón verde",
      map_url: "https://www.google.com/maps/search/?api=1&query=Calle%201",
      contact_names: ["Marta Ficticia"],
    },
    equipment: null,
    ...overrides,
  };
}

function payload(orders: Order[], crew: CrewOrders["crew"] = { name: "Escuadrilla 1" }) {
  return { crew, today: TODAY, orders } satisfies CrewOrders;
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function stubOrders(...responses: (() => Response)[]) {
  const fetchMock = vi.fn(async () => (responses.length > 1 ? responses.shift()! : responses[0])());
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderPage(state?: unknown) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const onLogout = vi.fn();
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[{ pathname: "/", state }]}>
        <Routes>
          <Route path="/" element={<MyOrdersPage onLogout={onLogout} />} />
          <Route path="/ordenes/:orderId" element={<DetailStub />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return { onLogout };
}

function DetailStub() {
  const { orderId } = useParams();
  return <h1>Detalle {orderId}</h1>;
}

afterEach(() => vi.restoreAllMocks());

describe("MyOrdersPage", () => {
  // Criterios 1 y 2: la escuadrilla y sus órdenes, en el orden de la API, con lo de la tarjeta.
  it("muestra la escuadrilla y cada orden con lo necesario para ir", async () => {
    stubOrders(() =>
      json(
        payload([
          order({ number: 7 }),
          order({
            number: 3,
            status: "in_progress",
            work_type_name: "Mantenimiento",
            description: "Preventivo trimestral",
            scheduled_for: "2026-10-27",
            equipment: {
              location_note: "Habitación 12",
              equipment_type_name: "Aire acondicionado",
              brand: "Marca Ficticia",
              model: "X1",
            },
          }),
        ]),
      ),
    );
    renderPage();

    expect(await screen.findByRole("heading", { name: "Escuadrilla 1" })).toBeInTheDocument();
    expect(screen.getByText("2 órdenes para hacer.")).toBeInTheDocument();
    const [primera, segunda] = screen.getAllByRole("article");

    const a = within(primera);
    expect(a.getByText("N° 7")).toBeInTheDocument();
    expect(a.getByText("Reparación")).toBeInTheDocument();
    expect(a.getByText("Asignada")).toBeInTheDocument();
    expect(a.getByText("Cámara no enfría")).toBeInTheDocument();
    expect(a.getByText("Sanatorio Ficticio")).toBeInTheDocument();
    expect(a.getByText("Calle 1")).toBeInTheDocument();
    expect(a.getByText("Sin equipo")).toBeInTheDocument();
    expect(a.getByText("Hoy")).toBeInTheDocument();

    const b = within(segunda);
    expect(b.getByText("N° 3")).toBeInTheDocument();
    expect(b.getByText("En curso")).toBeInTheDocument();
    expect(b.getByText("Habitación 12 · Aire acondicionado")).toBeInTheDocument();
    expect(b.getByText("Mañana")).toBeInTheDocument();
  });

  // Criterio 3: una orden con la fecha pasada se marca como vencida.
  it("marca como vencida una orden con la fecha prevista pasada", async () => {
    stubOrders(() => json(payload([order({ scheduled_for: "2026-10-25" })])));
    renderPage();

    const card = await screen.findByRole("article");
    expect(within(card).getByText("Vencida · Ayer")).toBeInTheDocument();
  });

  // Criterio 4: al actualizar, una orden que ya no es de la escuadrilla deja de verse.
  it("al actualizar deja de mostrar una orden que ya no es de la escuadrilla", async () => {
    const fetchMock = stubOrders(
      () => json(payload([order({ number: 7 }), order({ number: 8 })])),
      () => json(payload([order({ number: 8 })])),
    );
    renderPage();
    expect(await screen.findByText("N° 7")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Actualizar" }));

    await screen.findByText("1 orden para hacer.");
    expect(screen.queryByText("N° 7")).not.toBeInTheDocument();
    expect(screen.getByText("N° 8")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  // Criterio 6: escuadrilla sin trabajo.
  it("avisa cuando la escuadrilla no tiene trabajo asignado", async () => {
    stubOrders(() => json(payload([])));
    renderPage();

    expect(await screen.findByText("No tienen trabajo asignado.")).toBeInTheDocument();
    expect(screen.queryByRole("article")).not.toBeInTheDocument();
  });

  // Criterio 7: usuario sin escuadrilla activa.
  it("pide avisar a administración si el usuario no tiene escuadrilla", async () => {
    stubOrders(() => json(payload([], null)));
    renderPage();

    expect(
      await screen.findByText(
        "Este usuario no tiene una escuadrilla asignada. Avisale a administración.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole("article")).not.toBeInTheDocument();
  });

  it("avisa si no se pudieron cargar las órdenes", async () => {
    stubOrders(() => json({ detail: { code: "x", message: "x" } }, 500));
    renderPage();

    expect(
      await screen.findByText("No se pudieron cargar las órdenes. Revisá la conexión."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Actualizar" })).toBeInTheDocument();
  });

  it("si falla al actualizar, avisa y deja la última lista", async () => {
    stubOrders(
      () => json(payload([order({ number: 7 })])),
      () => json({ detail: { code: "x", message: "x" } }, 500),
    );
    renderPage();
    expect(await screen.findByText("N° 7")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Actualizar" }));

    expect(
      await screen.findByText("No se pudo actualizar. Se muestra la última lista cargada."),
    ).toBeInTheDocument();
    expect(screen.getByText("N° 7")).toBeInTheDocument();
  });

  // E05-02: tocar una tarjeta abre el detalle de esa orden.
  it("al tocar una tarjeta abre el detalle de la orden", async () => {
    const id = "6f1c2a9e-0000-4000-8000-000000000001";
    stubOrders(() => json(payload([order({ id, number: 7 })])));
    renderPage();

    await userEvent.click(await screen.findByText("N° 7"));

    expect(screen.getByRole("heading", { name: `Detalle ${id}` })).toBeInTheDocument();
  });

  it("cierra la sesión", async () => {
    stubOrders(() => json(payload([])));
    const { onLogout } = renderPage();

    await userEvent.click(await screen.findByRole("button", { name: "Cerrar sesión" }));

    expect(onLogout).toHaveBeenCalled();
  });

  // E05-04: al volver de un cierre, la lista lo confirma.
  it("muestra el aviso del cierre recién enviado", async () => {
    stubOrders(() => json(payload([])));
    renderPage({ notice: "Orden N° 3 cerrada." });

    expect(await screen.findByRole("status")).toHaveTextContent("Orden N° 3 cerrada.");
  });
});
