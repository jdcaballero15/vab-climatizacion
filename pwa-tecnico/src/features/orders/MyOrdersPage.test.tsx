import { QueryClient, QueryClientProvider, onlineManager } from "@tanstack/react-query";
import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useParams } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "../../api/schema";
import { deleteClosureDraft, memory, saveClosureDraft } from "../../test/memoryClosureDrafts";
import { EMPTY_DRAFT } from "./closure";
import type { StoredClosure } from "./closureDrafts";
import { MyOrdersPage } from "./MyOrdersPage";

vi.mock("./closureDrafts", () => import("../../test/memoryClosureDrafts"));

const USER_ID = "90000000-0000-4000-8000-000000000001";

/** Guarda un cierre en el celular de prueba. */
function store(orderId: string, overrides: Partial<StoredClosure> = {}) {
  const closure: StoredClosure = {
    userId: USER_ID,
    orderId,
    status: "draft",
    problem: null,
    order: { number: 9, workTypeName: "Service", clientName: "Clínica Ficticia" },
    draft: EMPTY_DRAFT,
    idempotencyKey: `clave-${orderId}`,
    photos: [],
    signature: null,
    ...overrides,
  };
  memory.set(`${closure.userId}/${orderId}`, closure);
}

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

type CrewDone = components["schemas"]["CrewDoneOrdersTechnicianOut"];
type DoneOrder = components["schemas"]["DoneOrderTechnicianOut"];

function doneOrder(overrides: Partial<DoneOrder> = {}): DoneOrder {
  return {
    id: crypto.randomUUID(),
    number: 5,
    work_type_name: "Service",
    description: "Limpieza de filtros",
    client_name: "Clínica Ficticia",
    address: "Calle 2",
    outcome: "done",
    not_done_reason: null,
    // 17:30 del 26/10 en Argentina, el día de TODAY.
    closed_at: "2026-10-26T20:30:00Z",
    ...overrides,
  };
}

// "Hechas esta semana" (E05-14) se pide aparte; por defecto, sin cierres.
let doneResponse: () => Response;

function stubDone(orders: DoneOrder[], crew: CrewDone["crew"] = { name: "Escuadrilla 1" }) {
  doneResponse = () => json({ crew, orders } satisfies CrewDone);
}

/** Responde la lista de abiertas en el orden dado; devuelve las llamadas a esa lista. */
function stubOrders(...responses: (() => Response)[]) {
  const fetchMock = vi.fn(async () => (responses.length > 1 ? responses.shift()! : responses[0])());
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: Request) =>
      new URL(input.url).pathname.endsWith("/tech/orders/done") ? doneResponse() : fetchMock(),
    ),
  );
  return fetchMock;
}

function renderPage(state?: unknown) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const onLogout = vi.fn();
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[{ pathname: "/", state }]}>
        <Routes>
          <Route path="/" element={<MyOrdersPage userId={USER_ID} onLogout={onLogout} />} />
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

beforeEach(() => {
  memory.clear();
  stubDone([]);
});
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

  // E05-13, criterio 2: la tarjeta avisa que hay un cierre empezado.
  it("marca las órdenes con un borrador del cierre", async () => {
    const withDraft = order({ number: 5, status: "in_progress" });
    store(withDraft.id);
    store(withDraft.id, { userId: "otro-usuario" });
    stubOrders(() => json(payload([withDraft, order({ number: 6 })])));
    renderPage();

    const cards = await screen.findAllByRole("article");
    expect(await within(cards[0]).findByText("Borrador")).toBeInTheDocument();
    expect(within(cards[1]).queryByText("Borrador")).not.toBeInTheDocument();
  });

  // E05-13, criterio 9: con un cierre sin enviar, avisa antes de cerrar sesión.
  it("con un borrador pide confirmar antes de cerrar sesión", async () => {
    const withDraft = order({ status: "in_progress" });
    store(withDraft.id);
    stubOrders(() => json(payload([withDraft])));
    const { onLogout } = renderPage();
    await screen.findByText("Borrador");

    await userEvent.click(screen.getByRole("button", { name: "Cerrar sesión" }));

    const warning = screen.getByRole("group", { name: "Confirmar cierre de sesión" });
    expect(warning).toHaveTextContent("Hay un cierre sin enviar.");
    expect(onLogout).not.toHaveBeenCalled();
    await userEvent.click(within(warning).getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByRole("group", { name: /Confirmar/ })).not.toBeInTheDocument();
    expect(onLogout).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: "Cerrar sesión" }));
    await userEvent.click(screen.getByRole("button", { name: "Cerrar sesión igual" }));
    expect(onLogout).toHaveBeenCalled();
    // El borrador no se borra: queda para cuando vuelva a entrar.
    expect(memory.size).toBe(1);
  });

  // Criterio 2: cada estado del cierre guardado se ve en la tarjeta.
  it("marca pendientes, rechazados y los que hay que revisar", async () => {
    const orders = [1, 2, 3].map((number) => order({ number, status: "in_progress" }));
    store(orders[0].id, { status: "pending" });
    store(orders[1].id, { status: "rejected" });
    store(orders[2].id, { problem: { field: "observation", message: "Escribí qué falta." } });
    stubOrders(() => json(payload(orders)));
    renderPage();

    const cards = await screen.findAllByRole("article");
    expect(await within(cards[0]).findByText("Pendiente de enviar")).toBeInTheDocument();
    expect(within(cards[1]).getByText("Rechazado")).toBeInTheDocument();
    expect(within(cards[2]).getByText("Revisar")).toBeInTheDocument();
  });

  // Criterio 6: la orden rechazada ya no viene en la lista, pero lo guardado se ve.
  it("muestra los cierres guardados de órdenes que ya no están en la lista", async () => {
    store("orden-cancelada", { status: "rejected" });
    stubOrders(() => json(payload([order({ number: 2 })])));
    renderPage();

    const saved = await screen.findByRole("region", { name: "Guardados en este celular" });
    expect(within(saved).getByText("N° 9")).toBeInTheDocument();
    expect(within(saved).getByText("Clínica Ficticia")).toBeInTheDocument();
    expect(within(saved).getByText("Rechazado")).toBeInTheDocument();
    expect(within(saved).getByRole("link")).toHaveAttribute(
      "href",
      "/ordenes/orden-cancelada/cerrar",
    );
  });

  it("sin conexión muestra igual los cierres guardados", async () => {
    store("orden-1", { status: "pending" });
    stubOrders(() => {
      throw new TypeError("Failed to fetch");
    });
    renderPage();

    const saved = await screen.findByRole("region", { name: "Guardados en este celular" });
    expect(within(saved).getByText("Pendiente de enviar")).toBeInTheDocument();
  });

  // Sin señal el navegador está offline y TanStack Query pausa la consulta, sin error.
  it("con el celular offline avisa que no hay señal y muestra lo guardado", async () => {
    store("orden-1", { status: "pending" });
    const fetchMock = stubOrders(() => json(payload([])));
    onlineManager.setOnline(false);
    try {
      renderPage();

      expect(await screen.findByText(/No hay señal/)).toBeInTheDocument();
      const saved = screen.getByRole("region", { name: "Guardados en este celular" });
      expect(within(saved).getByText("Pendiente de enviar")).toBeInTheDocument();
      expect(fetchMock).not.toHaveBeenCalled();
    } finally {
      onlineManager.setOnline(true);
    }
  });

  it("cuando el reintento manda un cierre, la tarjeta se actualiza sola", async () => {
    const pending = order({ status: "in_progress" });
    store(pending.id, { status: "pending" });
    stubOrders(() => json(payload([pending])));
    renderPage();
    await screen.findByText("Pendiente de enviar");

    await act(() =>
      saveClosureDraft({ ...memory.get(`${USER_ID}/${pending.id}`)!, status: "rejected" }),
    );

    expect(await screen.findByText("Rechazado")).toBeInTheDocument();
  });

  it("cuando el reintento manda el cierre pendiente, el aviso lo dice", async () => {
    store("orden-1", { status: "pending" });
    stubOrders(() => json(payload([])));
    renderPage({
      notice: "Sin señal. Quedó pendiente.",
      pending: true,
      orderId: "orden-1",
      sentNotice: "Se envió el cierre de la orden N° 9.",
    });
    expect(await screen.findByRole("status")).toHaveTextContent("Sin señal. Quedó pendiente.");

    await act(() => deleteClosureDraft(USER_ID, "orden-1"));

    const status = await screen.findByText("Se envió el cierre de la orden N° 9.");
    expect(status).not.toHaveClass("orders__notice--pending");
  });

  it("el aviso de un cierre pendiente se muestra distinto al de uno enviado", async () => {
    stubOrders(() => json(payload([])));
    renderPage({ notice: "Sin señal. Quedó pendiente.", pending: true });

    expect(await screen.findByRole("status")).toHaveClass("orders__notice--pending");
  });
});

// E05-14: los cierres de la escuadrilla en los últimos 7 días.
describe("MyOrdersPage, hechas esta semana", () => {
  // Criterio 1: las dos pestañas con su contador.
  it("muestra las pestañas con cuántas hay en cada una", async () => {
    stubOrders(() => json(payload([order({ number: 7 })])));
    stubDone([doneOrder(), doneOrder({ number: 6 })]);
    renderPage();

    expect(await screen.findByRole("button", { name: "Hechas esta semana (2)" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Para hacer (1)" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  // Criterios 1 y 2: cada cierre con su resultado y la hora, sin abrirse.
  it("lista los cierres con el resultado y la hora, sin link", async () => {
    stubOrders(() => json(payload([order({ number: 7 })])));
    stubDone([
      doneOrder(),
      doneOrder({
        number: 4,
        outcome: "not_done",
        not_done_reason: "client_absent",
        closed_at: "2026-10-25T12:05:00Z",
      }),
      doneOrder({ number: 3, outcome: "needs_revisit", closed_at: "2026-10-21T21:00:00Z" }),
    ]);
    renderPage();

    await userEvent.click(await screen.findByRole("button", { name: /Hechas esta semana/ }));

    const lista = screen.getByRole("list", { name: "Hechas esta semana" });
    const [resuelta, ausente, otraVisita] = within(lista).getAllByRole("article");
    expect(within(resuelta).getByText("N° 5")).toBeInTheDocument();
    expect(within(resuelta).getByText("Resuelta")).toBeInTheDocument();
    expect(within(resuelta).getByText("Hoy 17:30")).toBeInTheDocument();
    expect(within(resuelta).getByText("Clínica Ficticia")).toBeInTheDocument();
    expect(within(resuelta).getByText("Calle 2")).toBeInTheDocument();
    expect(within(ausente).getByText("No se pudo hacer")).toBeInTheDocument();
    expect(within(ausente).getByText("Cliente ausente o sin acceso")).toBeInTheDocument();
    expect(within(ausente).getByText("Ayer 09:05")).toBeInTheDocument();
    expect(within(otraVisita).getByText("Requiere otra visita")).toBeInTheDocument();
    expect(within(otraVisita).getByText("21/10/2026 18:00")).toBeInTheDocument();
    expect(within(lista).queryByRole("link")).not.toBeInTheDocument();
    // Las abiertas no se ven en esta pestaña.
    expect(screen.queryByText("N° 7")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /Para hacer/ }));
    expect(screen.getByText("N° 7")).toBeInTheDocument();
  });

  // Criterio 6: sin cierres en la semana.
  it("avisa si no cerraron órdenes en los últimos 7 días", async () => {
    stubOrders(() => json(payload([order()])));
    renderPage();

    await userEvent.click(await screen.findByRole("button", { name: "Hechas esta semana (0)" }));

    expect(screen.getByText("No cerraron órdenes en los últimos 7 días.")).toBeInTheDocument();
  });

  it("avisa si no se pudieron cargar las hechas", async () => {
    stubOrders(() => json(payload([order()])));
    doneResponse = () => json({ detail: "error" }, 500);
    renderPage();

    await userEvent.click(await screen.findByRole("button", { name: "Hechas esta semana" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No se pudieron cargar las órdenes hechas.",
    );
  });

  // Criterio 6: sin escuadrilla no hay pestañas, como en "Para hacer".
  it("sin escuadrilla no muestra las pestañas", async () => {
    stubOrders(() => json(payload([], null)));
    stubDone([], null);
    renderPage();

    expect(
      await screen.findByText(
        "Este usuario no tiene una escuadrilla asignada. Avisale a administración.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Hechas esta semana/ })).not.toBeInTheDocument();
  });
});
