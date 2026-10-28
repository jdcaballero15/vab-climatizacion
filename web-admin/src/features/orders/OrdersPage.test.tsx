import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ClientSummary, Site } from "../clients/types";
import type { Crew } from "../crews/types";
import { businessToday, nextDay } from "./labels";
import { OrdersPage } from "./OrdersPage";
import type { ClosureDetail, OrderListItem, WorkOrder } from "./types";

const SANATORIO: ClientSummary = {
  id: "c1",
  number: "10642",
  name: "Sanatorio Ficticio",
  segment: "healthcare",
};
const MAPS = "https://www.google.com/maps/search/?api=1&query=";
const CENTRAL: Site = {
  id: "s1",
  client_id: "c1",
  label: "Central",
  address: "Av. Belgrano 123",
  reference: null,
  is_active: true,
  equipment_count: 0,
  map_url: `${MAPS}x`,
};
const ANEXO: Site = { ...CENTRAL, id: "s2", label: "Anexo", address: "Ruta 9" };
const VIEJO: Site = { ...CENTRAL, id: "s3", label: "Viejo", is_active: false };
const TIPOS = [
  { id: "w1", name: "Reparación", is_active: true },
  { id: "w2", name: "Service", is_active: true },
];
const PENDIENTE: OrderListItem = {
  id: "o1",
  number: 7,
  status: "pending",
  client_id: "c1",
  client_name: "Sanatorio Ficticio",
  site_label: "Central",
  site_address: "Av. Belgrano 123",
  work_type_name: "Reparación",
  description: "No enfría",
  created_at: "2026-10-05T13:00:00Z",
  returned: null,
  assignment: null,
  cancellation: null,
  completed: null,
};
const OTRA_PENDIENTE: OrderListItem = {
  ...PENDIENTE,
  id: "o2",
  number: 8,
  site_label: null,
  site_address: "Ruta 9",
  work_type_name: "Service",
  created_at: "2026-10-20T13:00:00Z",
};
// La API devuelve solo las activas, ya ordenadas (E02-09).
const ESCUADRILLAS: Crew[] = [
  {
    id: "c1",
    name: "Escuadrilla 1",
    is_active: true,
    app_user: { id: "u1", full_name: "Celular 1", email: "c1@ot-demo.com", is_active: true },
  },
  { id: "c2", name: "Escuadrilla 2", is_active: true, app_user: null },
];
const CREADA: WorkOrder = {
  id: "o9",
  number: 9,
  kind: "on_site",
  source: "manual",
  status: "pending",
  client_id: "c1",
  client_site_id: "s1",
  work_type_id: "w1",
  channel: "whatsapp",
  description: "Pierde agua",
  requester_name: null,
  requester_area: null,
  created_at: "2026-10-26T13:00:00Z",
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const EN_CURSO: OrderListItem = {
  ...PENDIENTE,
  id: "o4",
  number: 4,
  status: "in_progress",
  assignment: { crew_name: "Escuadrilla 1", scheduled_for: "2026-10-27" },
};
const ASIGNADA: OrderListItem = {
  ...EN_CURSO,
  id: "o5",
  number: 5,
  status: "assigned",
  assignment: { crew_name: "Escuadrilla 2", scheduled_for: "2026-10-29" },
};
const TERMINADA: OrderListItem = {
  ...PENDIENTE,
  id: "o3",
  number: 3,
  status: "done",
  completed: { crew_name: "Escuadrilla 1", closed_at: "2026-10-26T18:00:00Z" },
};
const CIERRE: ClosureDetail = {
  outcome: "done",
  closed_at: "2026-10-26T18:00:00Z",
  closed_by_name: "Celular 1",
  crew_name: "Escuadrilla 1",
  technicians: ["Ana Ficticia", "Beto Inventado"],
  tasks: ["Carga de gas", "Limpieza de filtros"],
  failure: "Pérdida de gas",
  repair: "Soldadura en la cañería",
  equipment_condition: "working_with_notes",
  not_done_reason: null,
  observation: "Revisar en un mes.",
  photos: [],
  signature: null,
  no_signature_reason: null,
  no_signature_text: null,
};
const CANCELADA: OrderListItem = {
  ...PENDIENTE,
  id: "o6",
  number: 6,
  status: "cancelled",
  cancellation: {
    reason: "other",
    reason_text: "Se mudó el local",
    cancelled_by_name: "Admin Ficticia",
    cancelled_at: "2026-10-26T15:00:00Z",
  },
};

function pendingPage(items: OrderListItem[], total = items.length, offset = 0) {
  return { items, total, limit: 50, offset };
}

type Handler = (request: Request, url: URL) => Response | Promise<Response | undefined> | undefined;

/** Mock de fetch con lo mínimo para el alta; cada test pisa lo que necesita. */
function mockApi(handler: Handler = () => undefined, sites: Site[] = [CENTRAL]) {
  const fetchMock = vi.fn(async (request: Request) => {
    const url = new URL(request.url);
    const response = await handler(request, url);
    if (response) {
      return response;
    }
    if (url.pathname.endsWith("/admin/clients/similar")) {
      return json([SANATORIO]);
    }
    if (url.pathname.endsWith("/sites")) {
      return json(sites);
    }
    if (url.pathname.endsWith("/admin/work-types")) {
      return json(TIPOS);
    }
    if (url.pathname.endsWith("/admin/crews")) {
      return json(ESCUADRILLAS);
    }
    if (url.pathname.endsWith("/admin/orders") && request.method === "GET") {
      return json(pendingPage([]));
    }
    return json({}, 404);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function calls(fetchMock: ReturnType<typeof mockApi>, method: string, pathEnd: string) {
  return fetchMock.mock.calls
    .map(([request]) => request as Request)
    .filter((request) => request.method === method)
    .filter((request) => new URL(request.url).pathname.endsWith(pathEnd));
}

/** Pedidos del listado de un estado, sin contar los de las cifras (que piden una sola orden). */
function listados(fetchMock: ReturnType<typeof mockApi>, status: string) {
  return calls(fetchMock, "GET", "/admin/orders").filter((request) => {
    const params = new URL(request.url).searchParams;
    return params.get("status") === status && params.get("limit") !== "1";
  });
}

function renderOrders() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <OrdersPage />
    </QueryClientProvider>,
  );
}

const ESTADOS: Record<string, string> = {
  pending: "Pendientes",
  assigned: "Asignadas",
  in_progress: "En curso",
  done: "Terminadas",
  cancelled: "Canceladas",
};

/** El alta está detrás del botón "Nueva orden". */
async function abrirAlta() {
  await userEvent.click(screen.getByRole("button", { name: "Nueva orden" }));
}

/** Las acciones secundarias están en el menú de tres puntos de la tarjeta. */
async function abrirMenu(user: ReturnType<typeof userEvent.setup>, numero: number) {
  await user.click(
    await screen.findByRole("button", { name: `Más acciones de la orden N° ${numero}` }),
  );
}

// Sección y no formulario: adentro va también el alta de domicilio, que es otro formulario.
function formulario() {
  return screen.getByRole("region", { name: "Nueva orden" });
}

async function elegirCliente(user: ReturnType<typeof userEvent.setup>) {
  await user.type(within(formulario()).getByLabelText("Cliente"), "sanatorio");
  await user.click(await screen.findByRole("button", { name: /Elegir Sanatorio Ficticio/ }));
}

async function completarPedido(user: ReturnType<typeof userEvent.setup>) {
  const form = formulario();
  await user.selectOptions(await within(form).findByLabelText("Tipo de trabajo"), "w1");
  await user.selectOptions(within(form).getByLabelText("Canal"), "whatsapp");
  await user.type(within(form).getByLabelText("Descripción del pedido"), "Pierde agua");
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("OrdersPage", () => {
  it("lista las pendientes con número, cliente, domicilio, tipo y fecha", async () => {
    mockApi((request, url) =>
      url.pathname.endsWith("/admin/orders") && request.method === "GET"
        ? json(pendingPage([PENDIENTE, OTRA_PENDIENTE]))
        : undefined,
    );
    renderOrders();

    const tabla = await screen.findByRole("list", { name: "Órdenes pendientes" });
    const filas = within(tabla).getAllByRole("listitem");
    expect(filas).toHaveLength(2);
    expect(within(filas[0]).getByText("N° 7")).toBeInTheDocument();
    expect(within(filas[0]).getByText("Sanatorio Ficticio")).toBeInTheDocument();
    expect(within(filas[0]).getByText("Central")).toBeInTheDocument();
    expect(within(filas[0]).getByText("Reparación")).toBeInTheDocument();
    expect(within(filas[0]).getByText("05/10/2026")).toBeInTheDocument();
    expect(within(filas[1]).getByText("Ruta 9")).toBeInTheDocument();
  });

  it("indica por qué volvió de la escuadrilla", async () => {
    const otraVisita: OrderListItem = {
      ...PENDIENTE,
      returned: {
        crew_id: "c1",
        crew_name: "Escuadrilla 1",
        closed_at: "2026-10-27T14:00:00Z",
        outcome: "needs_revisit",
        not_done_reason: null,
        observation: "Falta el capacitor.",
      },
    };
    const noSePudo: OrderListItem = {
      ...OTRA_PENDIENTE,
      returned: {
        crew_id: "c2",
        crew_name: "Escuadrilla 2",
        closed_at: "2026-10-26T14:00:00Z",
        outcome: "not_done",
        not_done_reason: "client_absent",
        observation: null,
      },
    };
    mockApi((request, url) =>
      url.pathname.endsWith("/admin/orders") && request.method === "GET"
        ? json(pendingPage([otraVisita, noSePudo, { ...PENDIENTE, id: "o3", number: 9 }]))
        : undefined,
    );
    renderOrders();

    const tabla = await screen.findByRole("list", { name: "Órdenes pendientes" });
    expect(
      within(tabla).getByText(
        "Volvió de Escuadrilla 1 el 27/10/2026: Requiere otra visita. Falta el capacitor.",
      ),
    ).toBeInTheDocument();
    expect(
      within(tabla).getByText(
        "Volvió de Escuadrilla 2 el 26/10/2026: No se pudo hacer. Cliente ausente o sin acceso",
      ),
    ).toBeInTheDocument();
    // Tres órdenes y dos con el motivo: la que nunca salió no tiene.
    expect(within(tabla).getAllByRole("listitem")).toHaveLength(3);
  });

  it("avisa cuando no hay pendientes", async () => {
    mockApi();
    renderOrders();

    expect(await screen.findByText("No hay órdenes pendientes.")).toBeInTheDocument();
  });

  it("pide al menos 4 letras para buscar el cliente", async () => {
    const user = userEvent.setup();
    const fetchMock = mockApi();
    renderOrders();
    await abrirAlta();

    await user.type(within(formulario()).getByLabelText("Cliente"), "san");

    expect(screen.getByText("Escribí al menos 4 letras del nombre.")).toBeInTheDocument();
    expect(calls(fetchMock, "GET", "/admin/clients/similar")).toHaveLength(0);
  });

  it("crea una orden con un cliente de un solo domicilio, que se completa solo", async () => {
    const user = userEvent.setup();
    const fetchMock = mockApi((request, url) =>
      url.pathname.endsWith("/admin/orders") && request.method === "POST"
        ? json(CREADA, 201)
        : undefined,
    );
    renderOrders();
    await abrirAlta();

    await elegirCliente(user);
    const form = formulario();
    expect(await within(form).findByText("Domicilio: Central")).toBeInTheDocument();
    await completarPedido(user);
    await user.type(within(form).getByLabelText("Quién pidió"), "Jefa de mantenimiento");
    await user.type(within(form).getByLabelText("Dónde"), "Piso 3");
    await user.click(within(form).getByRole("button", { name: "Crear orden" }));

    expect(await screen.findByText("Orden N° 9 creada.")).toBeInTheDocument();
    const [post] = calls(fetchMock, "POST", "/admin/orders");
    expect(await post.json()).toEqual({
      client_id: "c1",
      client_site_id: "s1",
      work_type_id: "w1",
      channel: "whatsapp",
      description: "Pierde agua",
      requester_name: "Jefa de mantenimiento",
      requester_area: "Piso 3",
    });
    // Se refresca el listado de pendientes.
    await waitFor(() => expect(listados(fetchMock, "pending")).toHaveLength(2));
    // El formulario queda listo para el próximo pedido, sin la búsqueda anterior.
    expect(within(form).getByLabelText("Cliente")).toHaveValue("");
    expect(within(form).queryByRole("button", { name: /Elegir/ })).not.toBeInTheDocument();
    expect(within(form).getByLabelText("Descripción del pedido")).toHaveValue("");
  });

  it("con varios domicilios hay que elegir uno; los inactivos no se ofrecen", async () => {
    const user = userEvent.setup();
    const fetchMock = mockApi(
      (request, url) =>
        url.pathname.endsWith("/admin/orders") && request.method === "POST"
          ? json(CREADA, 201)
          : undefined,
      [CENTRAL, ANEXO, VIEJO],
    );
    renderOrders();
    await abrirAlta();

    await elegirCliente(user);
    const form = formulario();
    const domicilio = await within(form).findByLabelText("Domicilio");
    expect(domicilio).toHaveValue("");
    expect(within(domicilio).queryByRole("option", { name: "Viejo" })).not.toBeInTheDocument();
    await completarPedido(user);
    await user.click(within(form).getByRole("button", { name: "Crear orden" }));

    expect(await within(form).findByRole("alert")).toHaveTextContent("Falta el domicilio.");
    expect(calls(fetchMock, "POST", "/admin/orders")).toHaveLength(0);

    await user.selectOptions(domicilio, "s2");
    await user.click(within(form).getByRole("button", { name: "Crear orden" }));
    await screen.findByText("Orden N° 9 creada.");
    const [post] = calls(fetchMock, "POST", "/admin/orders");
    expect((await post.json()).client_site_id).toBe("s2");
  });

  it("sin domicilio activo, deja agregarlo sin salir de la pantalla", async () => {
    const user = userEvent.setup();
    let sitios: Site[] = [VIEJO];
    const fetchMock = mockApi((request, url) => {
      if (url.pathname.endsWith("/sites") && request.method === "POST") {
        sitios = [VIEJO, CENTRAL];
        return json(CENTRAL, 201);
      }
      if (url.pathname.endsWith("/sites")) {
        return json(sitios);
      }
      return undefined;
    });
    renderOrders();
    await abrirAlta();

    await elegirCliente(user);
    const form = formulario();
    expect(await within(form).findByText("El cliente no tiene domicilios activos.")).toBeVisible();
    const alta = screen.getByRole("form", { name: "Agregar domicilio" });
    await user.type(within(alta).getByLabelText("Dirección"), "Av. Belgrano 123");
    await user.click(within(alta).getByRole("button", { name: "Agregar domicilio" }));

    expect(await within(form).findByText("Domicilio: Central")).toBeInTheDocument();
    const [post] = calls(fetchMock, "POST", "/admin/clients/c1/sites");
    expect((await post.json()).address).toBe("Av. Belgrano 123");
  });

  it("indica todos los datos que faltan", async () => {
    const user = userEvent.setup();
    const fetchMock = mockApi();
    renderOrders();
    await abrirAlta();

    await user.click(within(formulario()).getByRole("button", { name: "Crear orden" }));

    expect(await within(formulario()).findByRole("alert")).toHaveTextContent(
      "Falta el cliente, el tipo de trabajo, el canal y la descripción.",
    );
    expect(calls(fetchMock, "POST", "/admin/orders")).toHaveLength(0);
  });

  it("muestra el error del backend", async () => {
    const user = userEvent.setup();
    mockApi((request, url) =>
      url.pathname.endsWith("/admin/orders") && request.method === "POST"
        ? json(
            {
              detail: {
                code: "work_type_inactive",
                message: "El tipo de trabajo está desactivado.",
              },
            },
            422,
          )
        : undefined,
    );
    renderOrders();
    await abrirAlta();

    await elegirCliente(user);
    await within(formulario()).findByText("Domicilio: Central");
    await completarPedido(user);
    await user.click(within(formulario()).getByRole("button", { name: "Crear orden" }));

    expect(await within(formulario()).findByRole("alert")).toHaveTextContent(
      "El tipo de trabajo está desactivado.",
    );
  });

  it("deja cambiar el cliente elegido", async () => {
    const user = userEvent.setup();
    mockApi();
    renderOrders();
    await abrirAlta();

    await elegirCliente(user);
    await user.click(within(formulario()).getByRole("button", { name: "Cambiar cliente" }));

    expect(within(formulario()).getByLabelText("Cliente")).toHaveValue("");
    expect(within(formulario()).queryByText("Domicilio: Central")).not.toBeInTheDocument();
  });

  describe("asignar", () => {
    function conPendiente(post?: (request: Request) => Response) {
      let asignada = false;
      return mockApi((request, url) => {
        if (url.pathname.endsWith("/assignment") && request.method === "POST") {
          const response = post
            ? post(request)
            : json(
                {
                  id: "a1",
                  work_order_id: "o1",
                  crew_id: "c2",
                  scheduled_for: "2099-01-15",
                  assigned_at: "2026-10-26T13:00:00Z",
                },
                201,
              );
          asignada = response.ok;
          return response;
        }
        if (url.pathname.endsWith("/admin/orders") && request.method === "GET") {
          return json(pendingPage(asignada ? [] : [PENDIENTE]));
        }
        return undefined;
      });
    }

    async function abrirAsignar(user: ReturnType<typeof userEvent.setup>) {
      await user.click(await screen.findByRole("button", { name: "Asignar la orden N° 7" }));
      return screen.getByRole("form", { name: "Asignar la orden N° 7" });
    }

    it("ofrece las escuadrillas activas y marca las que no tienen celular", async () => {
      const user = userEvent.setup();
      conPendiente();
      renderOrders();

      const form = await abrirAsignar(user);
      const escuadrilla = within(form).getByLabelText("Escuadrilla");
      await waitFor(() =>
        expect(
          within(escuadrilla)
            .getAllByRole("option")
            .map((o) => o.textContent),
        ).toEqual(["Elegí una escuadrilla", "Escuadrilla 1", "Escuadrilla 2 (sin celular)"]),
      );
      expect(within(form).getByLabelText("Fecha prevista")).toHaveAttribute("min");
    });

    it("asigna con escuadrilla y fecha y la orden sale del listado", async () => {
      const user = userEvent.setup();
      const fetchMock = conPendiente();
      renderOrders();

      const form = await abrirAsignar(user);
      await user.selectOptions(await within(form).findByLabelText("Escuadrilla"), "c2");
      await user.type(within(form).getByLabelText("Fecha prevista"), "2099-01-15");
      await user.click(within(form).getByRole("button", { name: "Confirmar asignación" }));

      expect(
        await screen.findByText("Orden N° 7 asignada a Escuadrilla 2 para el 15/01/2099."),
      ).toBeInTheDocument();
      const [post] = calls(fetchMock, "POST", "/admin/orders/o1/assignment");
      expect(await post.json()).toEqual({ crew_id: "c2", scheduled_for: "2099-01-15" });
      expect(await screen.findByText("No hay órdenes pendientes.")).toBeInTheDocument();
    });

    it("indica lo que falta sin llamar a la API", async () => {
      const user = userEvent.setup();
      const fetchMock = conPendiente();
      renderOrders();

      const form = await abrirAsignar(user);
      await user.click(within(form).getByRole("button", { name: "Confirmar asignación" }));

      expect(within(form).getByRole("alert")).toHaveTextContent(
        "Falta la escuadrilla y la fecha prevista.",
      );
      expect(calls(fetchMock, "POST", "/assignment")).toHaveLength(0);
    });

    it("muestra el error del backend", async () => {
      const user = userEvent.setup();
      conPendiente(() =>
        json(
          {
            detail: {
              code: "scheduled_date_in_past",
              message: "La fecha prevista no puede ser anterior a hoy.",
            },
          },
          422,
        ),
      );
      renderOrders();

      const form = await abrirAsignar(user);
      await user.selectOptions(await within(form).findByLabelText("Escuadrilla"), "c1");
      await user.type(within(form).getByLabelText("Fecha prevista"), "2099-01-15");
      await user.click(within(form).getByRole("button", { name: "Confirmar asignación" }));

      expect(await within(form).findByRole("alert")).toHaveTextContent(
        "La fecha prevista no puede ser anterior a hoy.",
      );
    });

    it("se puede cancelar", async () => {
      const user = userEvent.setup();
      conPendiente();
      renderOrders();

      const form = await abrirAsignar(user);
      await user.click(within(form).getByRole("button", { name: "Cancelar" }));

      expect(screen.queryByRole("form", { name: "Asignar la orden N° 7" })).not.toBeInTheDocument();
    });
  });
  describe("listado por estado", () => {
    function porEstado(cierre: ClosureDetail = CIERRE) {
      return mockApi((request, url) => {
        if (url.pathname.endsWith("/admin/orders/o3/closure")) {
          return json(cierre);
        }
        if (!(url.pathname.endsWith("/admin/orders") && request.method === "GET")) {
          return undefined;
        }
        const items: Record<string, OrderListItem[]> = {
          pending: [PENDIENTE],
          assigned: [ASIGNADA],
          in_progress: [EN_CURSO],
          done: [TERMINADA],
          cancelled: [CANCELADA],
        };
        return json(pendingPage(items[url.searchParams.get("status") ?? ""] ?? []));
      });
    }

    it("muestra asignadas y en curso con escuadrilla y fecha, y solo se pueden cancelar", async () => {
      const user = userEvent.setup();
      const fetchMock = porEstado();
      renderOrders();

      await screen.findByRole("list", { name: "Órdenes pendientes" });
      await user.click(screen.getByRole("button", { name: "Asignadas" }));

      const tabla = await screen.findByRole("list", { name: "Órdenes asignadas" });
      const [fila] = within(tabla).getAllByRole("listitem");
      expect(within(fila).getByText("Escuadrilla 2")).toBeInTheDocument();
      expect(within(fila).getByText("29/10/2026")).toBeInTheDocument();
      expect(
        within(fila).getByRole("button", { name: "Más acciones de la orden N° 5" }),
      ).toBeVisible();
      expect(within(fila).queryByRole("button", { name: /Asignar/ })).not.toBeInTheDocument();
      const [ultima] = listados(fetchMock, "assigned").slice(-1);
      expect(new URL(ultima.url).searchParams.get("status")).toBe("assigned");

      await user.click(screen.getByRole("button", { name: "En curso" }));
      const enCurso = await screen.findByRole("list", { name: "Órdenes en curso" });
      expect(within(enCurso).getByText("Escuadrilla 1")).toBeInTheDocument();
    });

    it("muestra cuántas hay en cada estado y las escuadrillas activas", async () => {
      porEstado();
      renderOrders();

      for (const nombre of ["Pendientes", "Asignadas", "En curso", "Terminadas"]) {
        expect(await screen.findByLabelText(`${nombre}: 1`)).toBeInTheDocument();
      }
      const escuadrillas = within(screen.getByRole("region", { name: "Escuadrillas activas" }));
      expect(await escuadrillas.findByText("Escuadrilla 1")).toBeInTheDocument();
      expect(escuadrillas.getByText("Celular 1")).toBeInTheDocument();
      expect(escuadrillas.getByText("Sin celular")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Pendientes" })).toHaveAttribute(
        "aria-pressed",
        "true",
      );
    });

    it("muestra las terminadas con escuadrilla y fecha de cierre, sin cancelar", async () => {
      const user = userEvent.setup();
      porEstado();
      renderOrders();

      await screen.findByRole("list", { name: "Órdenes pendientes" });
      await user.click(screen.getByRole("button", { name: "Terminadas" }));

      const tabla = await screen.findByRole("list", { name: "Órdenes terminadas" });
      const [fila] = within(tabla).getAllByRole("listitem");
      expect(within(fila).getByText("Escuadrilla 1")).toBeInTheDocument();
      expect(within(fila).getByText("26/10/2026")).toBeInTheDocument();
      expect(within(fila).queryByRole("button", { name: /Cancelar/ })).not.toBeInTheDocument();
    });

    it("muestra lo que cargó la escuadrilla al cerrar", async () => {
      const user = userEvent.setup();
      porEstado();
      renderOrders();

      await screen.findByRole("list", { name: "Órdenes pendientes" });
      await user.click(screen.getByRole("button", { name: "Terminadas" }));
      const ver = await screen.findByRole("button", { name: "Ver el cierre de la orden N° 3" });
      await user.click(ver);

      const detalle = await screen.findByLabelText("Cierre de la orden N° 3");
      const textos = within(detalle)
        .getAllByRole("definition")
        .map((dd) => dd.textContent);
      expect(textos).toEqual([
        "Resuelta",
        "Escuadrilla 1",
        "26/10/2026 por Celular 1",
        "Ana Ficticia, Beto Inventado",
        "Carga de gas, Limpieza de filtros",
        "Pérdida de gas",
        "Soldadura en la cañería",
        "Funciona con observaciones",
        "Revisar en un mes.",
      ]);
      expect(ver).toHaveTextContent("Ocultar cierre");

      await user.click(ver);
      expect(screen.queryByLabelText("Cierre de la orden N° 3")).not.toBeInTheDocument();
    });

    // E05-06, criterio 6: las fotos del cierre, en miniatura y para abrir grandes.
    it("muestra las fotos del cierre con su URL firmada", async () => {
      const user = userEvent.setup();
      const url = (n: number) =>
        `http://bucket.test/ot-files/closures/photos/${n}?X-Amz-Signature=s`;
      porEstado({
        ...CIERRE,
        photos: [
          { id: "f1", content_type: "image/jpeg", url: url(1) },
          { id: "f2", content_type: "image/jpeg", url: url(2) },
        ],
      });
      renderOrders();

      await screen.findByRole("list", { name: "Órdenes pendientes" });
      await user.click(screen.getByRole("button", { name: "Terminadas" }));
      await user.click(
        await screen.findByRole("button", { name: "Ver el cierre de la orden N° 3" }),
      );

      const detalle = await screen.findByLabelText("Cierre de la orden N° 3");
      const fotos = within(detalle).getAllByRole("img");
      expect(fotos.map((img) => img.getAttribute("alt"))).toEqual([
        "Foto 1 del cierre",
        "Foto 2 del cierre",
      ]);
      expect(fotos[1]).toHaveAttribute("src", url(2));
      const link = within(detalle).getByRole("link", { name: "Foto 1 del cierre" });
      expect(link).toHaveAttribute("href", url(1));
      expect(link).toHaveAttribute("target", "_blank");
    });

    async function verCierre(cierre: ClosureDetail) {
      const user = userEvent.setup();
      porEstado(cierre);
      renderOrders();
      await screen.findByRole("list", { name: "Órdenes pendientes" });
      await user.click(screen.getByRole("button", { name: "Terminadas" }));
      await user.click(
        await screen.findByRole("button", { name: "Ver el cierre de la orden N° 3" }),
      );
      return screen.findByLabelText("Cierre de la orden N° 3");
    }

    // E05-07, criterio 6: la firma con el nombre y la hora, con su URL firmada.
    it("muestra la firma del cliente con el nombre y la hora", async () => {
      const url = "http://bucket.test/ot-files/closures/signatures/1?X-Amz-Signature=s";
      const detalle = await verCierre({
        ...CIERRE,
        signature: {
          signer_name: "Rosa Ficticia",
          signed_at: "2026-10-28T20:18:01Z",
          url,
        },
      });

      const firma = within(detalle).getByRole("img", { name: "Firma de Rosa Ficticia" });
      expect(firma).toHaveAttribute("src", url);
      expect(within(detalle).getByRole("link", { name: "Firma de Rosa Ficticia" })).toHaveAttribute(
        "href",
        url,
      );
      // 20:18 UTC son las 17:18 en la hora de la empresa.
      expect(within(detalle).getByText("Rosa Ficticia · 28/10/2026 17:18")).toBeInTheDocument();
      expect(within(detalle).queryByText("Sin firma")).not.toBeInTheDocument();
    });

    it("muestra por qué no hay firma, con el texto si es Otro", async () => {
      const ausente = await verCierre({ ...CIERRE, no_signature_reason: "client_absent" });
      expect(within(ausente).getByText("Sin firma").nextSibling).toHaveTextContent(
        "Cliente ausente",
      );
      expect(within(ausente).queryByRole("img")).not.toBeInTheDocument();
    });

    it('con "Otro" muestra el texto de por qué no firma', async () => {
      const otro = await verCierre({
        ...CIERRE,
        no_signature_reason: "other",
        no_signature_text: "Se fue antes de terminar",
      });
      expect(within(otro).getByText("Sin firma").nextSibling).toHaveTextContent(
        "Se fue antes de terminar",
      );
    });

    it("un cierre anterior a la firma no muestra firma ni motivo", async () => {
      const detalle = await verCierre(CIERRE);
      expect(within(detalle).queryByText("Firma")).not.toBeInTheDocument();
      expect(within(detalle).queryByText("Sin firma")).not.toBeInTheDocument();
    });

    it("muestra las canceladas con motivo, quién y cuándo, sin acciones", async () => {
      const user = userEvent.setup();
      porEstado();
      renderOrders();

      await screen.findByRole("list", { name: "Órdenes pendientes" });
      await user.click(screen.getByRole("button", { name: "Canceladas" }));

      const tabla = await screen.findByRole("list", { name: "Órdenes canceladas" });
      const [fila] = within(tabla).getAllByRole("listitem");
      expect(within(fila).getByText("Se mudó el local")).toBeInTheDocument();
      expect(within(fila).getByText("Admin Ficticia")).toBeInTheDocument();
      expect(within(fila).getByText("26/10/2026")).toBeInTheDocument();
      expect(within(tabla).queryByRole("button")).not.toBeInTheDocument();
    });
  });

  describe("cancelar", () => {
    function conOrden(orden: OrderListItem, post?: (request: Request) => Response) {
      let cancelada = false;
      return mockApi((request, url) => {
        if (url.pathname.endsWith("/cancellation") && request.method === "POST") {
          const response = post
            ? post(request)
            : json(
                {
                  reason: "duplicate",
                  reason_text: null,
                  cancelled_by_name: "Admin Ficticia",
                  cancelled_at: "2026-10-27T13:00:00Z",
                },
                201,
              );
          cancelada = response.ok;
          return response;
        }
        if (url.pathname.endsWith("/admin/orders") && request.method === "GET") {
          const status = url.searchParams.get("status");
          return json(pendingPage(!cancelada && status === orden.status ? [orden] : []));
        }
        return undefined;
      });
    }

    async function abrirCancelar(user: ReturnType<typeof userEvent.setup>, numero = 7) {
      await abrirMenu(user, numero);
      await user.click(
        await screen.findByRole("button", { name: `Cancelar la orden N° ${numero}` }),
      );
      return screen.getByRole("form", { name: `Cancelar la orden N° ${numero}` });
    }

    it("cancela con un motivo de la lista y la orden sale del listado", async () => {
      const user = userEvent.setup();
      const fetchMock = conOrden(PENDIENTE);
      renderOrders();

      const form = await abrirCancelar(user);
      expect(
        within(within(form).getByLabelText("Motivo"))
          .getAllByRole("option")
          .map((o) => o.textContent),
      ).toEqual([
        "Elegí el motivo",
        "Cargada por error",
        "Duplicada",
        "El cliente la canceló",
        "Otro",
      ]);
      await user.selectOptions(within(form).getByLabelText("Motivo"), "duplicate");
      await user.click(within(form).getByRole("button", { name: "Confirmar cancelación" }));

      expect(await screen.findByText("Orden N° 7 cancelada.")).toBeInTheDocument();
      const [post] = calls(fetchMock, "POST", "/admin/orders/o1/cancellation");
      expect(await post.json()).toEqual({ reason: "duplicate", reason_text: null });
      expect(await screen.findByText("No hay órdenes pendientes.")).toBeInTheDocument();
    });

    it("sin motivo, o con Otro sin texto, no llama a la API", async () => {
      const user = userEvent.setup();
      const fetchMock = conOrden(PENDIENTE);
      renderOrders();

      const form = await abrirCancelar(user);
      await user.click(within(form).getByRole("button", { name: "Confirmar cancelación" }));
      expect(within(form).getByRole("alert")).toHaveTextContent("Falta el motivo.");

      await user.selectOptions(within(form).getByLabelText("Motivo"), "other");
      await user.type(within(form).getByLabelText("Cuál es el motivo"), "   ");
      await user.click(within(form).getByRole("button", { name: "Confirmar cancelación" }));
      expect(within(form).getByRole("alert")).toHaveTextContent("Falta escribir el motivo.");
      expect(calls(fetchMock, "POST", "/cancellation")).toHaveLength(0);
    });

    it("con Otro manda el texto escrito", async () => {
      const user = userEvent.setup();
      const fetchMock = conOrden(PENDIENTE);
      renderOrders();

      const form = await abrirCancelar(user);
      await user.selectOptions(within(form).getByLabelText("Motivo"), "other");
      await user.type(within(form).getByLabelText("Cuál es el motivo"), " Se mudó el local ");
      await user.click(within(form).getByRole("button", { name: "Confirmar cancelación" }));

      await screen.findByText("Orden N° 7 cancelada.");
      const [post] = calls(fetchMock, "POST", "/cancellation");
      expect(await post.json()).toEqual({ reason: "other", reason_text: "Se mudó el local" });
    });

    it("en curso avisa que la escuadrilla la está trabajando", async () => {
      const user = userEvent.setup();
      conOrden(EN_CURSO);
      renderOrders();

      await screen.findByText("No hay órdenes pendientes.");
      await user.click(screen.getByRole("button", { name: "En curso" }));
      const form = await abrirCancelar(user, 4);

      expect(within(form).getByRole("alert")).toHaveTextContent(
        "Escuadrilla 1 la está trabajando.",
      );
    });

    it("una pendiente no muestra el aviso de en curso", async () => {
      const user = userEvent.setup();
      conOrden(PENDIENTE);
      renderOrders();

      const form = await abrirCancelar(user);
      expect(within(form).queryByRole("alert")).not.toBeInTheDocument();
    });

    it("muestra el error del backend", async () => {
      const user = userEvent.setup();
      conOrden(PENDIENTE, () =>
        json(
          {
            detail: {
              code: "order_status_conflict",
              message: "Otra persona cambió la orden recién. Actualizá y probá de nuevo.",
            },
          },
          409,
        ),
      );
      renderOrders();

      const form = await abrirCancelar(user);
      await user.selectOptions(within(form).getByLabelText("Motivo"), "duplicate");
      await user.click(within(form).getByRole("button", { name: "Confirmar cancelación" }));

      expect(await within(form).findByRole("alert")).toHaveTextContent(
        "Otra persona cambió la orden recién.",
      );
    });

    it("se puede volver sin cancelar", async () => {
      const user = userEvent.setup();
      const fetchMock = conOrden(PENDIENTE);
      renderOrders();

      const form = await abrirCancelar(user);
      await user.click(within(form).getByRole("button", { name: "Volver" }));

      expect(
        screen.queryByRole("form", { name: "Cancelar la orden N° 7" }),
      ).not.toBeInTheDocument();
      expect(calls(fetchMock, "POST", "/cancellation")).toHaveLength(0);
    });
  });
  describe("reasignar, desasignar y reprogramar", () => {
    const ASIGNACION = {
      id: "a2",
      work_order_id: "o5",
      crew_id: "c1",
      scheduled_for: "2099-01-20",
      assigned_at: "2026-10-28T13:00:00Z",
    };
    const VOLVIO: OrderListItem = {
      ...PENDIENTE,
      returned: {
        crew_id: "c2",
        crew_name: "Escuadrilla 2",
        closed_at: "2026-10-27T14:00:00Z",
        outcome: "not_done",
        not_done_reason: "client_absent",
        observation: null,
      },
    };

    function conOrden(orden: OrderListItem, post?: (request: Request) => Response) {
      return mockApi((request, url) => {
        if (request.method === "POST" && /\/(re|un)?assignment$/.test(url.pathname)) {
          return post
            ? post(request)
            : url.pathname.endsWith("/unassignment")
              ? new Response(null, { status: 204 })
              : json({ ...ASIGNACION, work_order_id: orden.id }, 201);
        }
        if (url.pathname.endsWith("/admin/orders") && request.method === "GET") {
          return json(pendingPage(url.searchParams.get("status") === orden.status ? [orden] : []));
        }
        return undefined;
      });
    }

    async function verEstado(user: ReturnType<typeof userEvent.setup>, status: string) {
      await screen.findByRole("heading", { name: "Órdenes pendientes" });
      if (status !== "pending") {
        await user.click(screen.getByRole("button", { name: ESTADOS[status] }));
      }
    }

    it("una asignada se reasigna a otra escuadrilla con motivo", async () => {
      const user = userEvent.setup();
      const fetchMock = conOrden(ASIGNADA);
      renderOrders();

      await verEstado(user, "assigned");
      await user.click(await screen.findByRole("button", { name: "Reasignar la orden N° 5" }));
      const form = screen.getByRole("form", { name: "Reasignar la orden N° 5" });
      expect(within(form).getByText("Ahora: Escuadrilla 2, 29/10/2026.")).toBeInTheDocument();
      expect(within(form).queryByRole("alert")).not.toBeInTheDocument();
      await user.selectOptions(await within(form).findByLabelText("Escuadrilla"), "c1");
      await user.type(within(form).getByLabelText("Fecha prevista"), "2099-01-20");
      await user.type(within(form).getByLabelText("Motivo (opcional)"), "Se rompió la camioneta");
      await user.click(within(form).getByRole("button", { name: "Confirmar reasignación" }));

      expect(
        await screen.findByText("Orden N° 5 reasignada a Escuadrilla 1 para el 20/01/2099."),
      ).toBeInTheDocument();
      const [post] = calls(fetchMock, "POST", "/admin/orders/o5/reassignment");
      expect(await post.json()).toEqual({
        crew_id: "c1",
        scheduled_for: "2099-01-20",
        reason: "Se rompió la camioneta",
      });
    });

    it("una en curso se reasigna con aviso y no se puede desasignar", async () => {
      const user = userEvent.setup();
      conOrden(EN_CURSO);
      renderOrders();

      await verEstado(user, "in_progress");
      await user.click(await screen.findByRole("button", { name: "Reasignar la orden N° 4" }));

      const form = screen.getByRole("form", { name: "Reasignar la orden N° 4" });
      expect(within(form).getByRole("alert")).toHaveTextContent(
        "Escuadrilla 1 la está trabajando.",
      );
      expect(
        screen.queryByRole("button", { name: "Desasignar la orden N° 4" }),
      ).not.toBeInTheDocument();
    });

    it("muestra el error de la API", async () => {
      const user = userEvent.setup();
      conOrden(ASIGNADA, () =>
        json(
          {
            detail: {
              code: "same_assignment",
              message: "Ya está asignada a esa escuadrilla para ese día.",
              field: "crew_id",
            },
          },
          422,
        ),
      );
      renderOrders();

      await verEstado(user, "assigned");
      await user.click(await screen.findByRole("button", { name: "Reasignar la orden N° 5" }));
      const form = screen.getByRole("form", { name: "Reasignar la orden N° 5" });
      await user.selectOptions(await within(form).findByLabelText("Escuadrilla"), "c2");
      await user.type(within(form).getByLabelText("Fecha prevista"), "2099-01-20");
      await user.click(within(form).getByRole("button", { name: "Confirmar reasignación" }));

      expect(await within(form).findByRole("alert")).toHaveTextContent(
        "Ya está asignada a esa escuadrilla para ese día.",
      );
    });

    it("una asignada se desasigna y vuelve a pendientes", async () => {
      const user = userEvent.setup();
      const fetchMock = conOrden(ASIGNADA);
      renderOrders();

      await verEstado(user, "assigned");
      await abrirMenu(user, 5);
      await user.click(await screen.findByRole("button", { name: "Desasignar la orden N° 5" }));
      const form = screen.getByRole("form", { name: "Desasignar la orden N° 5" });
      expect(form).toHaveTextContent("desaparece del celular de Escuadrilla 2");
      await user.type(within(form).getByLabelText("Motivo (opcional)"), "Lo resolvió el cliente");
      await user.click(within(form).getByRole("button", { name: "Confirmar desasignación" }));

      expect(
        await screen.findByText("Orden N° 5 desasignada: volvió a Pendientes."),
      ).toBeInTheDocument();
      const [post] = calls(fetchMock, "POST", "/admin/orders/o5/unassignment");
      expect(await post.json()).toEqual({ reason: "Lo resolvió el cliente" });
    });

    it("una que volvió se reprograma con la misma escuadrilla y mañana", async () => {
      const user = userEvent.setup();
      const fetchMock = conOrden(VOLVIO);
      renderOrders();

      await user.click(await screen.findByRole("button", { name: "Reprogramar la orden N° 7" }));
      expect(
        screen.queryByRole("button", { name: "Asignar la orden N° 7" }),
      ).not.toBeInTheDocument();
      const form = screen.getByRole("form", { name: "Reprogramar la orden N° 7" });
      await waitFor(() => expect(within(form).getByLabelText("Escuadrilla")).toHaveValue("c2"));
      const manana = nextDay(businessToday());
      expect(within(form).getByLabelText("Fecha prevista")).toHaveValue(manana);
      await user.click(within(form).getByRole("button", { name: "Confirmar asignación" }));

      expect(
        await screen.findByText(/Orden N° 7 reprogramada a Escuadrilla 2/),
      ).toBeInTheDocument();
      const [post] = calls(fetchMock, "POST", "/admin/orders/o1/assignment");
      expect(await post.json()).toEqual({ crew_id: "c2", scheduled_for: manana });
    });
  });
});
