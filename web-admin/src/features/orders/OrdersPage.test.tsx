import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ClientSummary, Site } from "../clients/types";
import { OrdersPage } from "./OrdersPage";
import type { PendingOrder, WorkOrder } from "./types";

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
const PENDIENTE: PendingOrder = {
  id: "o1",
  number: 7,
  client_id: "c1",
  client_name: "Sanatorio Ficticio",
  site_label: "Central",
  site_address: "Av. Belgrano 123",
  work_type_name: "Reparación",
  description: "No enfría",
  created_at: "2026-10-05T13:00:00Z",
};
const OTRA_PENDIENTE: PendingOrder = {
  ...PENDIENTE,
  id: "o2",
  number: 8,
  site_label: null,
  site_address: "Ruta 9",
  work_type_name: "Service",
  created_at: "2026-10-20T13:00:00Z",
};
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

function pendingPage(items: PendingOrder[], total = items.length, offset = 0) {
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

    const tabla = await screen.findByRole("table", { name: "Órdenes pendientes" });
    const filas = within(tabla).getAllByRole("row").slice(1);
    expect(filas).toHaveLength(2);
    expect(within(filas[0]).getByText("7")).toBeInTheDocument();
    expect(within(filas[0]).getByText("Sanatorio Ficticio")).toBeInTheDocument();
    expect(within(filas[0]).getByText("Central")).toBeInTheDocument();
    expect(within(filas[0]).getByText("Reparación")).toBeInTheDocument();
    expect(within(filas[0]).getByText("05/10/2026")).toBeInTheDocument();
    expect(within(filas[1]).getByText("Ruta 9")).toBeInTheDocument();
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
    await waitFor(() => expect(calls(fetchMock, "GET", "/admin/orders")).toHaveLength(2));
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

    await elegirCliente(user);
    await user.click(within(formulario()).getByRole("button", { name: "Cambiar cliente" }));

    expect(within(formulario()).getByLabelText("Cliente")).toHaveValue("");
    expect(within(formulario()).queryByText("Domicilio: Central")).not.toBeInTheDocument();
  });
});
