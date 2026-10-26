import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ClientsPage } from "./ClientsPage";
import type { Client, ClientSummary, Contact, Site } from "./types";

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
  client_site_id: null,
  name: "Ana Pérez",
  phone: null,
  email: "ana@ejemplo.com",
  receives_monthly_report: true,
};
const MAPS = "https://www.google.com/maps/search/?api=1&query=";
const SEDE: Site = {
  id: "s1",
  client_id: "c1",
  label: "Sede central",
  address: "Av. Belgrano 123",
  reference: "Piso 2",
  is_active: true,
  map_url: `${MAPS}Av.%20Belgrano%20123%2C%20Santiago%20del%20Estero`,
};
const DEPOSITO: Site = {
  id: "s2",
  client_id: "c1",
  label: null,
  address: "Calle Falsa 742",
  reference: null,
  is_active: false,
  map_url: `${MAPS}Calle%20Falsa%20742%2C%20Santiago%20del%20Estero`,
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

type Handler = (request: Request, url: URL) => Response | Promise<Response | undefined> | undefined;

/** Mock de fetch: cada handler responde lo suyo; lo que no se atiende es un listado vacío. */
function mockApi(handler: Handler) {
  const fetchMock = vi.fn(async (request: Request) => {
    const url = new URL(request.url);
    const response = await handler(request, url);
    if (response) {
      return response;
    }
    if (url.pathname.endsWith("/contacts") || url.pathname.endsWith("/sites")) {
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
      client_site_id: null,
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
      client_site_id: null,
      name: "Ana Pérez",
      phone: "123",
      email: "ana@ejemplo.com",
      receives_monthly_report: true,
    });
  });

  describe("domicilios (E03-02)", () => {
    function conDomicilios(extra: Handler = () => undefined) {
      return mockApi(async (request, url) => {
        const propio = await extra(request, url);
        if (propio) {
          return propio;
        }
        if (url.pathname.endsWith("/admin/clients") && request.method === "GET") {
          return json(page([HOTEL]));
        }
        if (url.pathname.endsWith("/admin/clients/c1")) {
          return json(HOTEL);
        }
        if (url.pathname.endsWith("/c1/sites") && request.method === "GET") {
          return json([SEDE, DEPOSITO]);
        }
        return undefined;
      });
    }

    async function abrirFicha() {
      renderClients();
      await userEvent.click(await screen.findByRole("button", { name: "Ver Hotel Ficticio" }));
      return within(await screen.findByRole("region", { name: "Domicilios" }));
    }

    // Criterios 3 y 5: todos los domicilios, con etiqueta, dirección, referencia y mapa.
    it("lista activos e inactivos con su enlace al mapa", async () => {
      conDomicilios();
      const domicilios = await abrirFicha();

      const sede = within(await domicilios.findByRole("listitem", { name: "Sede central" }));
      expect(sede.getByText("Av. Belgrano 123")).toBeInTheDocument();
      expect(sede.getByText("Piso 2")).toBeInTheDocument();
      expect(sede.getByRole("link", { name: "Ver en el mapa" })).toHaveAttribute(
        "href",
        SEDE.map_url,
      );
      const deposito = within(domicilios.getByRole("listitem", { name: "Calle Falsa 742" }));
      expect(deposito.getByText("Inactivo")).toBeInTheDocument();
    });

    // Criterio 1: alcanza con la dirección; etiqueta y referencia opcionales.
    it("agrega un domicilio", async () => {
      const fetchMock = conDomicilios((request, url) =>
        url.pathname.endsWith("/c1/sites") && request.method === "POST"
          ? json({ ...SEDE, id: "s3" }, 201)
          : undefined,
      );
      const domicilios = await abrirFicha();

      const alta = within(domicilios.getByRole("form", { name: "Agregar domicilio" }));
      await userEvent.type(alta.getByLabelText("Etiqueta"), "Depósito");
      await userEvent.type(alta.getByLabelText("Dirección"), "Ruta 9 km 5, La Banda");
      await userEvent.click(alta.getByRole("button", { name: "Agregar domicilio" }));

      await waitFor(() => expect(calls(fetchMock, "POST", "/c1/sites")).toHaveLength(1));
      expect(await calls(fetchMock, "POST", "/c1/sites")[0].json()).toEqual({
        label: "Depósito",
        address: "Ruta 9 km 5, La Banda",
        reference: null,
      });
    });

    // Criterio 8: la dirección es obligatoria, también en el cliente.
    it("no manda un domicilio sin dirección", async () => {
      const fetchMock = conDomicilios();
      const domicilios = await abrirFicha();

      const alta = within(domicilios.getByRole("form", { name: "Agregar domicilio" }));
      await userEvent.type(alta.getByLabelText("Dirección"), "   ");
      await userEvent.click(alta.getByRole("button", { name: "Agregar domicilio" }));

      expect(await alta.findByText("La dirección es obligatoria.")).toBeInTheDocument();
      expect(calls(fetchMock, "POST", "/c1/sites")).toHaveLength(0);
    });

    // Criterio 2: se editan dirección, etiqueta y referencia, sin mandar campos de más.
    it("edita un domicilio", async () => {
      const fetchMock = conDomicilios((request, url) =>
        url.pathname.endsWith("/admin/sites/s1") && request.method === "PATCH"
          ? json({ ...SEDE, reference: "Piso 3" })
          : undefined,
      );
      const domicilios = await abrirFicha();

      await userEvent.click(await domicilios.findByRole("button", { name: "Editar Sede central" }));
      const edicion = within(domicilios.getByRole("form", { name: "Editar Sede central" }));
      await userEvent.clear(edicion.getByLabelText("Referencia"));
      await userEvent.type(edicion.getByLabelText("Referencia"), "Piso 3");
      await userEvent.click(edicion.getByRole("button", { name: "Guardar" }));

      await waitFor(() => expect(calls(fetchMock, "PATCH", "/admin/sites/s1")).toHaveLength(1));
      expect(await calls(fetchMock, "PATCH", "/admin/sites/s1")[0].json()).toEqual({
        label: "Sede central",
        address: "Av. Belgrano 123",
        reference: "Piso 3",
      });
    });

    // Criterio 4: se desactiva y se reactiva; no hay borrar.
    it("desactiva y reactiva domicilios", async () => {
      const fetchMock = conDomicilios((request, url) => {
        if (request.method !== "PATCH") {
          return undefined;
        }
        if (url.pathname.endsWith("/admin/sites/s1")) {
          return json({ ...SEDE, is_active: false });
        }
        if (url.pathname.endsWith("/admin/sites/s2")) {
          return json({ ...DEPOSITO, is_active: true });
        }
        return undefined;
      });
      const domicilios = await abrirFicha();

      await userEvent.click(
        await domicilios.findByRole("button", { name: "Desactivar Sede central" }),
      );
      await userEvent.click(domicilios.getByRole("button", { name: "Reactivar Calle Falsa 742" }));

      await waitFor(() => expect(calls(fetchMock, "PATCH", "/admin/sites/s2")).toHaveLength(1));
      expect(await calls(fetchMock, "PATCH", "/admin/sites/s1")[0].json()).toEqual({
        is_active: false,
      });
      expect(await calls(fetchMock, "PATCH", "/admin/sites/s2")[0].json()).toEqual({
        is_active: true,
      });
      expect(domicilios.queryByRole("button", { name: /Borrar/ })).not.toBeInTheDocument();
    });

    // Criterio 6: el contacto se asocia a un domicilio activo o queda como general.
    it("asocia un contacto a un domicilio y lo muestra en la lista", async () => {
      const fetchMock = conDomicilios((request, url) => {
        if (url.pathname.endsWith("/contacts") && request.method === "GET") {
          return json([{ ...ANA, client_site_id: "s1" }]);
        }
        if (url.pathname.endsWith("/contacts") && request.method === "POST") {
          return json({ ...ANA, id: "k2", name: "Beto", client_site_id: "s1" }, 201);
        }
        return undefined;
      });
      await abrirFicha();

      const ana = within(await screen.findByRole("listitem", { name: "Ana Pérez" }));
      expect(await ana.findByText("Sede central")).toBeInTheDocument();

      const alta = within(screen.getByRole("form", { name: "Agregar contacto" }));
      const selector = alta.getByLabelText("Domicilio");
      // Los domicilios inactivos no se ofrecen para asociar contactos nuevos.
      expect(
        within(selector).queryByRole("option", { name: "Calle Falsa 742" }),
      ).not.toBeInTheDocument();
      await userEvent.selectOptions(selector, "s1");
      await userEvent.type(alta.getByLabelText("Nombre del contacto"), "Beto");
      await userEvent.click(alta.getByRole("button", { name: "Agregar contacto" }));

      await waitFor(() => expect(calls(fetchMock, "POST", "/contacts")).toHaveLength(1));
      expect(await calls(fetchMock, "POST", "/contacts")[0].json()).toMatchObject({
        client_site_id: "s1",
        name: "Beto",
      });
    });
  });
});
