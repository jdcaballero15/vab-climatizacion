import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { businessToday } from "../orders/labels";
import { MaintenancePage } from "./MaintenancePage";
import type { CheckStep, MaintenancePlan, MaintenanceRun } from "./types";

const PLAN: MaintenancePlan = {
  id: "p1",
  equipment: {
    id: "e1",
    internal_code: "EA1064201",
    location_note: "Habitación 12",
    equipment_type_name: "Split",
  },
  client: {
    id: "c1",
    number: "10642",
    name: "Hotel Ficticio",
    site_label: "Central",
    site_address: "Calle 1",
  },
  work_type: { id: "w2", name: "Service" },
  crew: { id: "k1", name: "Escuadrilla 1" },
  every_months: 3,
  next_due_on: "2026-11-20",
  ends_on: null,
  notes: null,
  active: true,
  open_order: { id: "o9", number: 41, status: "pending", due_on: "2026-08-20" },
};
const SIN_ESCUADRILLA: MaintenancePlan = {
  ...PLAN,
  id: "p2",
  equipment: { ...PLAN.equipment, id: "e2", internal_code: "EA1064202" },
  crew: null,
  every_months: 1,
  open_order: null,
};
const CLIENTE = { id: "c1", number: "10642", name: "Hotel Ficticio", segment: "hotel" };
const SEDE = {
  id: "s1",
  client_id: "c1",
  label: "Central",
  address: "Calle 1",
  reference: null,
  is_active: true,
  equipment_count: 1,
  map_url: "https://www.google.com/maps/search/?api=1&query=x",
};
const EQUIPO = {
  id: "e3",
  client_site_id: "s1",
  equipment_type_id: "t1",
  internal_code: "EA1064203",
  location_note: "Terraza",
  brand: null,
  model: null,
  serial_number: null,
  notes: null,
};
const TIPOS = [
  { id: "w1", name: "Reparación", is_active: true },
  { id: "w2", name: "Service", is_active: true },
];
const PASOS: CheckStep[] = [
  { id: "s1", name: "Limpieza de filtros", position: 0, is_active: true },
  { id: "s2", name: "Revisión del drenaje", position: 1, is_active: true },
  { id: "s3", name: "Prueba de funcionamiento", position: 2, is_active: true },
];
const ESCUADRILLAS = [{ id: "k1", name: "Escuadrilla 1", is_active: true, app_user: null }];

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

function stubApi(handler?: (call: Call) => Response | undefined) {
  const calls: Call[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (request: Request) => {
      const url = new URL(request.url);
      const text = request.method === "GET" ? "" : await request.clone().text();
      const call = { method: request.method, path: url.pathname, body: text && JSON.parse(text) };
      calls.push(call);
      const custom = handler?.(call);
      if (custom) {
        return custom;
      }
      if (url.pathname.endsWith("/admin/maintenance/plans") && request.method === "GET") {
        return json([PLAN, SIN_ESCUADRILLA]);
      }
      if (url.pathname.endsWith("/admin/maintenance/check-steps") && request.method === "GET") {
        return json(PASOS);
      }
      if (url.pathname.endsWith("/admin/clients")) {
        return json({ items: [CLIENTE], total: 1, limit: 20, offset: 0 });
      }
      if (url.pathname.endsWith("/sites")) {
        return json([SEDE]);
      }
      if (url.pathname.endsWith("/equipment")) {
        return json([EQUIPO]);
      }
      if (url.pathname.endsWith("/admin/work-types")) {
        return json(TIPOS);
      }
      if (url.pathname.endsWith("/admin/crews")) {
        return json(ESCUADRILLAS);
      }
      return json({}, 404);
    }),
  );
  return calls;
}

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <MaintenancePage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("MaintenancePage", () => {
  // E07-03: cada plan con su equipo, frecuencia, próxima visita, escuadrilla y orden abierta.
  it("lista los planes", async () => {
    stubApi();
    renderPage();

    const tabla = await screen.findByRole("table", { name: "Planes de mantenimiento" });
    const [, primera, segunda] = within(tabla).getAllByRole("row");
    expect(primera).toHaveTextContent("Hotel Ficticio");
    expect(primera).toHaveTextContent("EA1064201 · Split · Habitación 12");
    expect(primera).toHaveTextContent("Cada 3 meses");
    expect(primera).toHaveTextContent("20/11/2026");
    expect(primera).toHaveTextContent("Escuadrilla 1");
    expect(within(primera).getByRole("link", { name: "N° 41 · Pendiente" })).toHaveAttribute(
      "href",
      "/ordenes/o9",
    );
    expect(segunda).toHaveTextContent("Todos los meses");
    expect(segunda).toHaveTextContent("Sin escuadrilla fija");
  });

  // E07-04, criterio 5: el resumen de la corrida, con lo omitido y por qué.
  it("genera ahora y muestra el resumen", async () => {
    const user = userEvent.setup();
    const resumen: MaintenanceRun = {
      generated: [
        {
          order_id: "o10",
          number: 42,
          client_name: "Hotel Ficticio",
          equipment_code: "EA1064201",
          due_on: "2026-11-20",
        },
      ],
      skipped: [{ plan_id: "p2", equipment_code: "EA1064202", reason: "equipment_deleted" }],
    };
    const calls = stubApi((call) =>
      call.path.endsWith("/admin/maintenance/run") ? json(resumen) : undefined,
    );
    renderPage();

    await user.click(screen.getByRole("button", { name: "Generar ahora" }));

    const estado = await screen.findByRole("status");
    expect(estado).toHaveTextContent("Se generó 1 orden: N° 42 (EA1064201).");
    expect(estado).toHaveTextContent(
      "No se generó EA1064202: el equipo o el cliente está dado de baja.",
    );
    expect(calls.filter((call) => call.path.endsWith("/run"))).toHaveLength(1);
  });

  // E07-03, criterio 2: terminar el plan le pone fin hoy.
  it("termina un plan con confirmación", async () => {
    const user = userEvent.setup();
    const calls = stubApi((call) =>
      call.method === "PATCH"
        ? json({ ...PLAN, ends_on: businessToday(), active: false })
        : undefined,
    );
    renderPage();

    await user.click(await screen.findByRole("button", { name: "Terminar el plan de EA1064201" }));
    await user.click(screen.getByRole("button", { name: "Terminar" }));

    await waitFor(() =>
      expect(calls.find((call) => call.method === "PATCH")).toEqual({
        method: "PATCH",
        path: expect.stringMatching(/\/admin\/maintenance\/plans\/p1$/),
        body: { ends_on: businessToday() },
      }),
    );
  });

  // E07-03, criterio 1: alta con equipo, frecuencia, próxima visita y escuadrilla.
  it("crea un plan con el tipo Service propuesto", async () => {
    const user = userEvent.setup();
    const calls = stubApi((call) =>
      call.method === "POST" && call.path.endsWith("/plans") ? json(PLAN, 201) : undefined,
    );
    renderPage();

    await user.click(screen.getByRole("button", { name: "Nuevo plan" }));
    const alta = screen.getByRole("region", { name: "Nuevo plan" });
    await user.type(within(alta).getByLabelText("Cliente"), "hotel");
    await user.click(await screen.findByRole("button", { name: /Elegir Hotel Ficticio/ }));
    await user.selectOptions(await within(alta).findByLabelText("Equipo"), "e3");
    await user.selectOptions(within(alta).getByLabelText("Frecuencia"), "6");
    await user.type(within(alta).getByLabelText("Próxima visita"), "2027-01-10");
    await user.selectOptions(
      within(alta).getByLabelText("Escuadrilla que suele ir (opcional)"),
      "k1",
    );
    await waitFor(() => expect(within(alta).getByLabelText("Tipo de trabajo")).toHaveValue("w2"));
    await user.click(within(alta).getByRole("button", { name: "Crear plan" }));

    await waitFor(() =>
      expect(calls.find((call) => call.method === "POST")?.body).toEqual({
        equipment_id: "e3",
        work_type_id: "w2",
        crew_id: "k1",
        every_months: 6,
        next_due_on: "2027-01-10",
        ends_on: null,
        notes: null,
      }),
    );
  });

  it("avisa lo que falta", async () => {
    const user = userEvent.setup();
    const calls = stubApi();
    renderPage();

    await user.click(screen.getByRole("button", { name: "Nuevo plan" }));
    const alta = screen.getByRole("region", { name: "Nuevo plan" });
    await user.click(within(alta).getByRole("button", { name: "Crear plan" }));

    expect(within(alta).getByRole("alert")).toHaveTextContent(
      "Falta el equipo y la próxima visita.",
    );
    expect(calls.filter((call) => call.method === "POST")).toHaveLength(0);
  });

  // E07-01: el checklist único, en orden, editable desde Mantenimiento.
  describe("checklist", () => {
    async function abrir() {
      const user = userEvent.setup();
      await user.click(screen.getByRole("button", { name: "Checklist" }));
      const lista = await screen.findByRole("list", { name: "Pasos del checklist" });
      await within(lista).findByText("Limpieza de filtros");
      return { user, lista };
    }

    it("muestra los pasos en orden", async () => {
      stubApi();
      renderPage();

      const { lista } = await abrir();

      expect(
        within(lista)
          .getAllByRole("listitem")
          .map((item) => item.textContent),
      ).toEqual([
        expect.stringContaining("Limpieza de filtros"),
        expect.stringContaining("Revisión del drenaje"),
        expect.stringContaining("Prueba de funcionamiento"),
      ]);
      expect(screen.getByRole("button", { name: "Subir Limpieza de filtros" })).toBeDisabled();
      expect(screen.getByRole("button", { name: "Bajar Prueba de funcionamiento" })).toBeDisabled();
    });

    it("agrega un paso", async () => {
      const calls = stubApi((call) =>
        call.method === "POST" && call.path.endsWith("/check-steps")
          ? json({ id: "s4", name: "Control de presiones", position: 3, is_active: true }, 201)
          : undefined,
      );
      renderPage();
      const { user } = await abrir();

      await user.type(screen.getByLabelText("Paso nuevo"), "Control de presiones");
      await user.click(screen.getByRole("button", { name: "Agregar paso" }));

      await waitFor(() =>
        expect(calls.find((call) => call.method === "POST")?.body).toEqual({
          name: "Control de presiones",
        }),
      );
    });

    it("baja un paso mandando el orden nuevo", async () => {
      const calls = stubApi((call) => (call.method === "PUT" ? json(PASOS) : undefined));
      renderPage();
      const { user } = await abrir();

      await user.click(screen.getByRole("button", { name: "Bajar Limpieza de filtros" }));

      await waitFor(() =>
        expect(calls.find((call) => call.method === "PUT")).toEqual({
          method: "PUT",
          path: expect.stringMatching(/\/admin\/maintenance\/check-steps\/order$/),
          body: { step_ids: ["s2", "s1", "s3"] },
        }),
      );
    });

    // Criterio 4: quitar un paso lo desactiva, no lo borra.
    it("desactiva un paso", async () => {
      const calls = stubApi((call) =>
        call.method === "PATCH" ? json({ ...PASOS[1], is_active: false }) : undefined,
      );
      renderPage();
      const { user } = await abrir();

      await user.click(screen.getByRole("button", { name: "Desactivar Revisión del drenaje" }));

      await waitFor(() =>
        expect(calls.find((call) => call.method === "PATCH")).toEqual({
          method: "PATCH",
          path: expect.stringMatching(/\/check-steps\/s2$/),
          body: { is_active: false },
        }),
      );
    });
  });
});
