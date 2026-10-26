import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { components } from "../../api/schema";
import { OrderDetailPage } from "./OrderDetailPage";

type OrderDetail = components["schemas"]["OrderDetailTechnicianOut"];

const ORDER_ID = "6f1c2a9e-0000-4000-8000-000000000001";
const MAP_URL = "https://www.google.com/maps/search/?api=1&query=Calle%201";

function detail(overrides: Partial<OrderDetail> = {}): OrderDetail {
  return {
    id: ORDER_ID,
    number: 3,
    status: "assigned",
    work_type_name: "Reparación",
    description: "Cámara no enfría. Mercadería en riesgo: ir primero.",
    client_name: "Sanatorio Ficticio",
    scheduled_for: "2026-10-26",
    today: "2026-10-26",
    requester_area: "Planta baja",
    site: {
      address: "Calle 1",
      reference: "Portón verde",
      map_url: MAP_URL,
      contact_names: ["Marta Ficticia", "Juan Ficticio"],
    },
    equipment: {
      location_note: "Habitación 12",
      equipment_type_name: "Aire acondicionado",
      brand: "Marca Ficticia",
      model: "X1",
    },
    tasks: ["Diagnosticar la falla", "Probar el funcionamiento"],
    ...overrides,
  };
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function stubFetch(response: () => Response) {
  const fetchMock = vi.fn<(request: Request) => Promise<Response>>(async () => response());
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderDetail() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[`/ordenes/${ORDER_ID}`]}>
        <Routes>
          <Route path="/" element={<h1>Lista de órdenes</h1>} />
          <Route path="/ordenes/:orderId" element={<OrderDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe("OrderDetailPage", () => {
  // Criterios 1 y 2: lo necesario para hacer el trabajo.
  it("muestra la orden con indicaciones, lugar, contactos y equipo", async () => {
    const fetchMock = stubFetch(() => json(detail()));
    renderDetail();

    expect(await screen.findByRole("heading", { name: "Sanatorio Ficticio" })).toBeInTheDocument();
    expect(new URL(fetchMock.mock.calls[0][0].url).pathname).toMatch(
      new RegExp(`/tech/orders/${ORDER_ID}$`),
    );
    expect(screen.getByText("N° 3")).toBeInTheDocument();
    expect(screen.getByText("Reparación")).toBeInTheDocument();
    expect(screen.getByText("Asignada")).toBeInTheDocument();
    expect(screen.getByText("Hoy")).toBeInTheDocument();
    expect(
      screen.getByText("Cámara no enfría. Mercadería en riesgo: ir primero."),
    ).toBeInTheDocument();
    expect(screen.getByText("Portón verde")).toBeInTheDocument();
    expect(screen.getByText("Planta baja")).toBeInTheDocument();
    expect(screen.getByText("Marta Ficticia, Juan Ficticio")).toBeInTheDocument();
    expect(
      screen.getByText("Habitación 12 · Aire acondicionado · Marca Ficticia X1"),
    ).toBeInTheDocument();
  });

  // Criterio 3: tareas del tipo de trabajo, de solo lectura.
  it("muestra las tareas del tipo de trabajo", async () => {
    stubFetch(() => json(detail()));
    renderDetail();

    const tareas = await screen.findByRole("list", { name: "Tareas" });
    expect(tareas).toHaveTextContent("Diagnosticar la falla");
    expect(tareas).toHaveTextContent("Probar el funcionamiento");
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  });

  it("avisa si el tipo de trabajo no tiene tareas", async () => {
    stubFetch(() => json(detail({ tasks: [] })));
    renderDetail();

    expect(
      await screen.findByText("Este tipo de trabajo no tiene tareas cargadas."),
    ).toBeInTheDocument();
  });

  // Criterio 4: la dirección abre la app de mapas.
  it("la dirección es un enlace al mapa", async () => {
    stubFetch(() => json(detail()));
    renderDetail();

    const enlace = await screen.findByRole("link", { name: "Calle 1" });
    expect(enlace).toHaveAttribute("href", MAP_URL);
  });

  it("marca vencida una orden con la fecha pasada y muestra sin equipo", async () => {
    stubFetch(() => json(detail({ scheduled_for: "2026-10-24", equipment: null })));
    renderDetail();

    expect(await screen.findByText("Vencida · 24/10/2026")).toBeInTheDocument();
    expect(screen.getByText("Sin equipo")).toBeInTheDocument();
  });

  it("omite el sector y los contactos si no hay", async () => {
    stubFetch(() =>
      json(
        detail({
          requester_area: null,
          site: { address: "Calle 1", reference: null, map_url: MAP_URL, contact_names: [] },
        }),
      ),
    );
    renderDetail();

    await screen.findByRole("heading", { name: "Sanatorio Ficticio" });
    expect(screen.queryByText("Sector")).not.toBeInTheDocument();
    expect(screen.queryByText("Contacto")).not.toBeInTheDocument();
  });

  // Criterio 6: una orden que ya no es de la escuadrilla.
  it("avisa si la orden no está entre las de la escuadrilla", async () => {
    stubFetch(() =>
      json({ detail: { code: "order_not_found", message: "No se encontró la orden." } }, 404),
    );
    renderDetail();

    expect(
      await screen.findByText("Esta orden ya no está entre las de tu escuadrilla."),
    ).toBeInTheDocument();
  });

  it("avisa si no se pudo cargar", async () => {
    stubFetch(() => json({ detail: { code: "x", message: "x" } }, 500));
    renderDetail();

    expect(
      await screen.findByText("No se pudo cargar la orden. Revisá la conexión."),
    ).toBeInTheDocument();
  });

  // Criterio 7: volver a la lista.
  it("vuelve a la lista de órdenes", async () => {
    stubFetch(() => json(detail()));
    renderDetail();

    await userEvent.click(await screen.findByRole("link", { name: "← Mis órdenes" }));

    expect(screen.getByRole("heading", { name: "Lista de órdenes" })).toBeInTheDocument();
  });

  // E05-03: iniciar la orden desde el detalle.
  describe("Iniciar", () => {
    function stubStart(get: () => Response, post: () => Response | Promise<Response>) {
      const posts: string[] = [];
      vi.stubGlobal(
        "fetch",
        vi.fn(async (request: Request) => {
          if (request.method === "POST") {
            posts.push(new URL(request.url).pathname);
            return post();
          }
          return get();
        }),
      );
      return posts;
    }

    // Criterio 1: pide confirmar y, si se cancela, no envía nada.
    it("pide confirmar antes de iniciar y cancelar no envía nada", async () => {
      const posts = stubStart(
        () => json(detail()),
        () => json(detail({ status: "in_progress" })),
      );
      renderDetail();

      await userEvent.click(await screen.findByRole("button", { name: "Iniciar" }));
      expect(screen.getByText("¿Empezar la orden N° 3?")).toBeInTheDocument();
      expect(posts).toEqual([]);

      await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));
      expect(screen.queryByText("¿Empezar la orden N° 3?")).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Iniciar" })).toBeInTheDocument();
      expect(posts).toEqual([]);
    });

    // Criterio 2: al confirmar queda En curso y desaparece el botón.
    it("al confirmar la orden queda En curso sin el botón", async () => {
      const posts = stubStart(
        () => json(detail()),
        () => json(detail({ status: "in_progress" })),
      );
      renderDetail();

      await userEvent.click(await screen.findByRole("button", { name: "Iniciar" }));
      await userEvent.click(screen.getByRole("button", { name: "Sí, empezar" }));

      expect(await screen.findByText("En curso")).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Iniciar" })).not.toBeInTheDocument();
      expect(posts).toHaveLength(1);
      expect(posts[0]).toMatch(new RegExp(`/tech/orders/${ORDER_ID}/start$`));
    });

    it("una orden En curso no muestra el botón", async () => {
      stubStart(
        () => json(detail({ status: "in_progress" })),
        () => json(detail({ status: "in_progress" })),
      );
      renderDetail();

      expect(await screen.findByText("En curso")).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Iniciar" })).not.toBeInTheDocument();
    });

    // Criterio 8: sin conexión avisa y la orden sigue Asignada para reintentar.
    it("si falla avisa y deja la orden Asignada para reintentar", async () => {
      stubStart(
        () => json(detail()),
        () => {
          throw new TypeError("sin conexión");
        },
      );
      renderDetail();

      await userEvent.click(await screen.findByRole("button", { name: "Iniciar" }));
      await userEvent.click(screen.getByRole("button", { name: "Sí, empezar" }));

      expect(
        await screen.findByText(
          "No se pudo iniciar la orden. Revisá la conexión e intentá de nuevo.",
        ),
      ).toBeInTheDocument();
      expect(screen.getByText("Asignada")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Iniciar" })).toBeInTheDocument();
    });

    // Criterio 4: si la orden ya no es de la escuadrilla, se avisa como en el detalle.
    it("si la orden ya no es de la escuadrilla lo avisa", async () => {
      stubStart(
        () => json(detail()),
        () =>
          json({ detail: { code: "order_not_found", message: "No se encontró la orden." } }, 404),
      );
      renderDetail();

      await userEvent.click(await screen.findByRole("button", { name: "Iniciar" }));
      await userEvent.click(screen.getByRole("button", { name: "Sí, empezar" }));

      expect(
        await screen.findByText("Esta orden ya no está entre las de tu escuadrilla."),
      ).toBeInTheDocument();
    });
  });
});
