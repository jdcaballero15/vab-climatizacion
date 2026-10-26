import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ClientsPage } from "./ClientsPage";
import type { Client, ClientSummary, Contact } from "./types";

const HOTEL: Client = {
  id: "c1",
  number: "10642",
  name: "Hotel Ficticio",
  segment: "hotel",
  tax_id: null,
  tax_condition: null,
  notes: null,
};
const PANADERIA: ClientSummary = {
  id: "c2",
  number: "10643",
  name: "Panadería El Trigal",
  segment: "unclassified",
};
const ANA: Contact = {
  id: "k1",
  client_id: "c1",
  name: "Ana Pérez",
  phone: null,
  email: "ana@ejemplo.com",
  receives_monthly_report: true,
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function page(items: ClientSummary[], total = items.length, offset = 0) {
  return { items, total, limit: 50, offset };
}

type Handler = (request: Request, url: URL) => Response | Promise<Response> | undefined;

/** Mock de fetch: cada handler responde lo suyo; lo que no se atiende es un listado vacío. */
function mockApi(handler: Handler) {
  const fetchMock = vi.fn(async (request: Request) => {
    const url = new URL(request.url);
    const response = await handler(request, url);
    if (response) {
      return response;
    }
    if (url.pathname.endsWith("/contacts")) {
      return json([]);
    }
    return json(page([]));
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

function renderClients() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ClientsPage />
    </QueryClientProvider>,
  );
}

function nuevoCliente() {
  return within(screen.getByRole("form", { name: "Nuevo cliente" }));
}

afterEach(() => vi.restoreAllMocks());

describe("ClientsPage", () => {
  // Criterio 10: listado con número, nombre y segmento, paginado.
  it("lista los clientes con número, nombre y segmento y pasa de página", async () => {
    const fetchMock = mockApi((request, url) => {
      if (request.method === "GET" && url.pathname.endsWith("/admin/clients")) {
        const offset = Number(url.searchParams.get("offset"));
        return json(page(offset === 0 ? [HOTEL] : [PANADERIA], 51, offset));
      }
      return undefined;
    });
    renderClients();

    expect(await screen.findByRole("cell", { name: "Hotel Ficticio" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "10642" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Hotel" })).toBeInTheDocument();
    expect(screen.getByText("1 a 1 de 51")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Siguiente" }));

    expect(await screen.findByRole("cell", { name: "Panadería El Trigal" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Sin clasificar" })).toBeInTheDocument();
    const ultima = calls(fetchMock, "GET", "/admin/clients").at(-1);
    expect(new URL(ultima!.url).searchParams.get("offset")).toBe("50");
    expect(screen.getByRole("button", { name: "Siguiente" })).toBeDisabled();
  });

  // Criterio 10: filtro por segmento.
  it("filtra por segmento", async () => {
    const fetchMock = mockApi(() => undefined);
    renderClients();

    await userEvent.selectOptions(screen.getByLabelText("Filtrar por segmento"), "hotel");

    await waitFor(() => {
      const ultima = calls(fetchMock, "GET", "/admin/clients").at(-1);
      expect(new URL(ultima!.url).searchParams.get("segment")).toBe("hotel");
    });
  });

  // Criterio 1: alcanza con el nombre; el segmento por defecto es "Sin clasificar".
  it("crea un cliente solo con el nombre", async () => {
    const fetchMock = mockApi((request, url) => {
      if (url.pathname.endsWith("/similar")) {
        return json([]);
      }
      if (request.method === "POST") {
        return json({ ...HOTEL, id: "c9", number: "1", name: "Cliente Nuevo" }, 201);
      }
      if (url.pathname.endsWith("/admin/clients/c9")) {
        return json({ ...HOTEL, id: "c9", number: "1", name: "Cliente Nuevo" });
      }
      return undefined;
    });
    renderClients();

    await userEvent.type(nuevoCliente().getByLabelText("Nombre o razón social"), "Cliente Nuevo");
    await userEvent.click(nuevoCliente().getByRole("button", { name: "Crear cliente" }));

    await waitFor(() => expect(calls(fetchMock, "POST", "/admin/clients")).toHaveLength(1));
    const body = await calls(fetchMock, "POST", "/admin/clients")[0].json();
    expect(body).toEqual({
      name: "Cliente Nuevo",
      segment: "unclassified",
      tax_id: null,
      tax_condition: null,
      notes: null,
    });
    // El cliente recién creado se abre para cargarle contactos.
    expect(await screen.findByText("Cliente N° 1: Cliente Nuevo")).toBeInTheDocument();
    expect(nuevoCliente().getByLabelText("Nombre o razón social")).toHaveValue("");
  });

  // Criterio 7: un nombre parecido se advierte; se puede guardar igual o cancelar.
  it("advierte de un nombre parecido y deja cancelar o guardar igual", async () => {
    const fetchMock = mockApi((request, url) => {
      if (url.pathname.endsWith("/similar")) {
        return json([{ ...PANADERIA, name: "Farmacia Del Sol", number: "77" }]);
      }
      if (request.method === "POST") {
        return json({ ...HOTEL, id: "c9", name: "Farmacia del Sol Termas" }, 201);
      }
      return undefined;
    });
    renderClients();

    const nombre = nuevoCliente().getByLabelText("Nombre o razón social");
    await userEvent.type(nombre, "Farmacia del Sol Termas");
    await userEvent.click(nuevoCliente().getByRole("button", { name: "Crear cliente" }));

    expect(await screen.findByText("Farmacia Del Sol (N° 77)")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(calls(fetchMock, "POST", "/admin/clients")).toHaveLength(0);

    await userEvent.click(nuevoCliente().getByRole("button", { name: "Crear cliente" }));
    await userEvent.click(await screen.findByRole("button", { name: "Guardar igual" }));

    await waitFor(() => expect(calls(fetchMock, "POST", "/admin/clients")).toHaveLength(1));
  });

  // Criterio 3: editar los datos del cliente.
  it("edita un cliente desde su ficha", async () => {
    const fetchMock = mockApi((request, url) => {
      if (url.pathname.endsWith("/admin/clients") && request.method === "GET") {
        return json(page([HOTEL]));
      }
      if (url.pathname.endsWith("/admin/clients/c1") && request.method === "GET") {
        return json(HOTEL);
      }
      if (url.pathname.endsWith("/admin/clients/c1") && request.method === "PATCH") {
        return json({ ...HOTEL, segment: "business", tax_condition: "monotributo" });
      }
      return undefined;
    });
    renderClients();

    await userEvent.click(await screen.findByRole("button", { name: "Ver Hotel Ficticio" }));
    const ficha = within(await screen.findByRole("form", { name: "Editar cliente" }));
    await userEvent.selectOptions(ficha.getByLabelText("Segmento"), "business");
    await userEvent.selectOptions(ficha.getByLabelText("Condición fiscal"), "monotributo");
    await userEvent.click(ficha.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => expect(calls(fetchMock, "PATCH", "/admin/clients/c1")).toHaveLength(1));
    const body = await calls(fetchMock, "PATCH", "/admin/clients/c1")[0].json();
    expect(body).toMatchObject({ segment: "business", tax_condition: "monotributo" });
    // Sin cambiar el nombre no se consulta por parecidos.
    expect(calls(fetchMock, "GET", "/similar")).toHaveLength(0);
  });

  // Criterio 4: contactos del cliente, con el informe mensual.
  it("muestra y agrega contactos", async () => {
    const fetchMock = mockApi((request, url) => {
      if (url.pathname.endsWith("/admin/clients") && request.method === "GET") {
        return json(page([HOTEL]));
      }
      if (url.pathname.endsWith("/admin/clients/c1")) {
        return json(HOTEL);
      }
      if (url.pathname.endsWith("/contacts") && request.method === "GET") {
        return json([ANA]);
      }
      if (url.pathname.endsWith("/contacts") && request.method === "POST") {
        return json({ ...ANA, id: "k2", name: null, phone: "3855000000", email: null }, 201);
      }
      return undefined;
    });
    renderClients();

    await userEvent.click(await screen.findByRole("button", { name: "Ver Hotel Ficticio" }));
    expect(await screen.findByText("Ana Pérez")).toBeInTheDocument();
    expect(screen.getByText("Informe mensual")).toBeInTheDocument();

    const alta = within(screen.getByRole("form", { name: "Agregar contacto" }));
    await userEvent.type(alta.getByLabelText("Teléfono"), "3855000000");
    await userEvent.click(alta.getByRole("button", { name: "Agregar contacto" }));

    await waitFor(() => expect(calls(fetchMock, "POST", "/contacts")).toHaveLength(1));
    expect(await calls(fetchMock, "POST", "/contacts")[0].json()).toEqual({
      name: null,
      phone: "3855000000",
      email: null,
      receives_monthly_report: false,
    });
  });

  // Criterio 5: el mensaje del backend se muestra tal cual.
  it("muestra el error del backend si el contacto del informe no tiene email", async () => {
    mockApi((request, url) => {
      if (url.pathname.endsWith("/admin/clients") && request.method === "GET") {
        return json(page([HOTEL]));
      }
      if (url.pathname.endsWith("/admin/clients/c1")) {
        return json(HOTEL);
      }
      if (url.pathname.endsWith("/contacts") && request.method === "POST") {
        return json(
          {
            detail: {
              code: "monthly_report_requires_email",
              message: "Para recibir el informe mensual, el contacto necesita un email.",
            },
          },
          422,
        );
      }
      return undefined;
    });
    renderClients();

    await userEvent.click(await screen.findByRole("button", { name: "Ver Hotel Ficticio" }));
    const alta = within(await screen.findByRole("form", { name: "Agregar contacto" }));
    await userEvent.type(alta.getByLabelText("Nombre del contacto"), "Beto");
    await userEvent.click(alta.getByLabelText("Recibe el informe mensual"));
    await userEvent.click(alta.getByRole("button", { name: "Agregar contacto" }));

    expect(
      await screen.findByText("Para recibir el informe mensual, el contacto necesita un email."),
    ).toBeInTheDocument();
  });

  // Al editar un contacto se mandan solo los campos editables.
  it("edita un contacto sin mandar id ni client_id", async () => {
    const fetchMock = mockApi((request, url) => {
      if (url.pathname.endsWith("/admin/clients") && request.method === "GET") {
        return json(page([HOTEL]));
      }
      if (url.pathname.endsWith("/admin/clients/c1")) {
        return json(HOTEL);
      }
      if (url.pathname.endsWith("/contacts") && request.method === "GET") {
        return json([ANA]);
      }
      if (url.pathname.endsWith("/contacts/k1") && request.method === "PATCH") {
        return json({ ...ANA, phone: "123" });
      }
      return undefined;
    });
    renderClients();

    await userEvent.click(await screen.findByRole("button", { name: "Ver Hotel Ficticio" }));
    await userEvent.click(await screen.findByRole("button", { name: "Editar Ana Pérez" }));
    const edicion = within(screen.getByRole("form", { name: "Editar Ana Pérez" }));
    await userEvent.type(edicion.getByLabelText("Teléfono"), "123");
    await userEvent.click(edicion.getByRole("button", { name: "Guardar" }));

    await waitFor(() => expect(calls(fetchMock, "PATCH", "/contacts/k1")).toHaveLength(1));
    expect(await calls(fetchMock, "PATCH", "/contacts/k1")[0].json()).toEqual({
      name: "Ana Pérez",
      phone: "123",
      email: "ana@ejemplo.com",
      receives_monthly_report: true,
    });
  });
});
