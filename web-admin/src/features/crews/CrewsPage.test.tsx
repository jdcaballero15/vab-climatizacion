import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { UserAdmin } from "../users/types";
import { CrewsPage } from "./CrewsPage";
import type { Crew, FieldTechnician } from "./types";

const CELU_1: UserAdmin = {
  id: "u1",
  email: "celular1@ot-demo.com",
  full_name: "Celular 1",
  role: "technician",
  is_active: true,
};
const CELU_2: UserAdmin = { ...CELU_1, id: "u2", email: "c2@ot-demo.com", full_name: "Celular 2" };
const CELU_3: UserAdmin = { ...CELU_1, id: "u3", email: "c3@ot-demo.com", full_name: "Celular 3" };
const CELU_BAJA: UserAdmin = {
  ...CELU_1,
  id: "u4",
  email: "c4@ot-demo.com",
  full_name: "Celular de baja",
  is_active: false,
};
const ADMIN: UserAdmin = {
  ...CELU_1,
  id: "u5",
  email: "admin@ot-demo.com",
  full_name: "Admin Ficticio",
  role: "admin",
};
const USUARIOS = [CELU_1, CELU_2, CELU_3, CELU_BAJA, ADMIN];

const UNO: Crew = {
  id: "c1",
  name: "Escuadrilla 1",
  is_active: true,
  app_user: { id: "u1", full_name: "Celular 1", email: "celular1@ot-demo.com", is_active: true },
};
const DOS: Crew = { id: "c2", name: "Escuadrilla 2", is_active: true, app_user: null };
const TRES: Crew = {
  id: "c3",
  name: "Escuadrilla 3",
  is_active: true,
  app_user: { id: "u2", full_name: "Celular 2", email: "c2@ot-demo.com", is_active: true },
};
const DIEGO: FieldTechnician = { id: "t1", full_name: "Diego Ficticio", is_active: true };

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
      const body = request.method === "GET" ? null : await request.clone().json();
      const call = { method: request.method, path: url.pathname, body };
      calls.push(call);
      const custom = handler?.(call);
      if (custom) {
        return custom;
      }
      if (url.pathname.endsWith("/admin/crews")) {
        return json([UNO, DOS, TRES]);
      }
      if (url.pathname.endsWith("/admin/field-technicians")) {
        return json([DIEGO]);
      }
      if (url.pathname.endsWith("/admin/users")) {
        return json(USUARIOS);
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
      <CrewsPage />
    </QueryClientProvider>,
  );
}

function seccion(nombre: string) {
  return screen.getByRole("region", { name: nombre });
}

afterEach(() => vi.unstubAllGlobals());

describe("CrewsPage", () => {
  it("lista las escuadrillas con el usuario de su celular", async () => {
    stubApi();
    renderPage();

    const escuadrillas = seccion("Escuadrillas");
    expect(await within(escuadrillas).findByText("Escuadrilla 1")).toBeInTheDocument();
    expect(within(escuadrillas).getByLabelText("Celular de Escuadrilla 1")).toHaveValue("u1");
    expect(within(escuadrillas).getByLabelText("Celular de Escuadrilla 2")).toHaveValue("");
  });

  it("ofrece solo técnicos activos libres, más el actual", async () => {
    stubApi();
    renderPage();

    const select = await within(seccion("Escuadrillas")).findByLabelText(
      "Celular de Escuadrilla 1",
    );
    await waitFor(() =>
      expect(
        within(select)
          .getAllByRole("option")
          .map((o) => o.textContent),
      ).toEqual(["Sin celular", "Celular 1", "Celular 3"]),
    );
  });

  it("asocia y desasocia el usuario del celular", async () => {
    const user = userEvent.setup();
    const calls = stubApi((call) =>
      call.method === "PATCH" ? json({ ...DOS, app_user: null }) : undefined,
    );
    renderPage();

    const dos = await within(seccion("Escuadrillas")).findByLabelText("Celular de Escuadrilla 2");
    await waitFor(() => expect(within(dos).getAllByRole("option")).toHaveLength(2));
    await user.selectOptions(dos, "u3");
    await user.selectOptions(
      within(seccion("Escuadrillas")).getByLabelText("Celular de Escuadrilla 1"),
      "",
    );

    const patches = calls.filter((c) => c.method === "PATCH");
    expect(patches).toEqual([
      {
        method: "PATCH",
        path: expect.stringMatching(/\/admin\/crews\/c2$/),
        body: { app_user_id: "u3" },
      },
      {
        method: "PATCH",
        path: expect.stringMatching(/\/admin\/crews\/c1$/),
        body: { app_user_id: null },
      },
    ]);
  });

  it("muestra el error del backend al asociar un usuario", async () => {
    const user = userEvent.setup();
    stubApi((call) =>
      call.method === "PATCH"
        ? json(
            {
              detail: {
                code: "crew_user_not_available",
                message: "Elegí un usuario técnico activo que no sea de otra escuadrilla.",
              },
            },
            422,
          )
        : undefined,
    );
    renderPage();

    const dos = await within(seccion("Escuadrillas")).findByLabelText("Celular de Escuadrilla 2");
    await waitFor(() => expect(within(dos).getAllByRole("option")).toHaveLength(2));
    await user.selectOptions(dos, "u3");

    expect(await within(seccion("Escuadrillas")).findByRole("alert")).toHaveTextContent(
      "Elegí un usuario técnico activo que no sea de otra escuadrilla.",
    );
  });

  it("marca el usuario asociado si quedó inactivo", async () => {
    stubApi((call) =>
      call.path.endsWith("/admin/crews")
        ? json([{ ...UNO, app_user: { ...UNO.app_user, is_active: false } }])
        : undefined,
    );
    renderPage();

    expect(
      await within(seccion("Escuadrillas")).findByText("El usuario del celular está inactivo."),
    ).toBeInTheDocument();
  });

  it("crea una escuadrilla y avisa si el nombre ya existe", async () => {
    const user = userEvent.setup();
    let intentos = 0;
    const calls = stubApi((call) => {
      if (call.method === "POST") {
        intentos += 1;
        return intentos === 1
          ? json({ ...DOS, id: "c9", name: "Escuadrilla 4" }, 201)
          : json(
              {
                detail: {
                  code: "crew_name_already_exists",
                  message: "Ya existe una escuadrilla con ese nombre (puede estar desactivada).",
                },
              },
              409,
            );
      }
      return undefined;
    });
    renderPage();

    const escuadrillas = seccion("Escuadrillas");
    await user.type(within(escuadrillas).getByLabelText("Nueva escuadrilla"), "Escuadrilla 4");
    await user.click(within(escuadrillas).getByRole("button", { name: "Agregar escuadrilla" }));
    await waitFor(() => expect(calls.filter((c) => c.method === "POST")).toHaveLength(1));
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({ name: "Escuadrilla 4" });

    await user.type(within(escuadrillas).getByLabelText("Nueva escuadrilla"), "Escuadrilla 1");
    await user.click(within(escuadrillas).getByRole("button", { name: "Agregar escuadrilla" }));
    expect(await within(escuadrillas).findByRole("alert")).toHaveTextContent(
      "Ya existe una escuadrilla con ese nombre (puede estar desactivada).",
    );
  });

  it("desactiva una escuadrilla", async () => {
    const user = userEvent.setup();
    const calls = stubApi((call) =>
      call.method === "PATCH" ? json({ ...UNO, is_active: false }) : undefined,
    );
    renderPage();

    await user.click(
      await within(seccion("Escuadrillas")).findByRole("button", {
        name: "Desactivar Escuadrilla 1",
      }),
    );

    await waitFor(() =>
      expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({ is_active: false }),
    );
  });

  it("explica por qué no se puede desactivar una escuadrilla con órdenes abiertas", async () => {
    const user = userEvent.setup();
    stubApi((call) =>
      call.method === "PATCH"
        ? json(
            {
              detail: {
                code: "crew_has_open_orders",
                message: "Tiene órdenes asignadas o en curso. Reasignalas antes de desactivarla.",
              },
            },
            409,
          )
        : undefined,
    );
    renderPage();

    await user.click(
      await within(seccion("Escuadrillas")).findByRole("button", {
        name: "Desactivar Escuadrilla 1",
      }),
    );

    const alerta = await within(seccion("Escuadrillas")).findByRole("alert");
    expect(alerta).toHaveTextContent(
      "Tiene órdenes asignadas o en curso. Reasignalas antes de desactivarla.",
    );
    expect(alerta).not.toHaveTextContent("Ya existe");
  });

  it("lista, crea y desactiva técnicos", async () => {
    const user = userEvent.setup();
    const calls = stubApi((call) => {
      if (call.method === "POST") {
        return json({ id: "t2", full_name: "Ana Ficticia", is_active: true }, 201);
      }
      if (call.method === "PATCH") {
        return json({ ...DIEGO, is_active: false });
      }
      return undefined;
    });
    renderPage();

    const tecnicos = seccion("Técnicos");
    expect(await within(tecnicos).findByText("Diego Ficticio")).toBeInTheDocument();
    await user.type(within(tecnicos).getByLabelText("Nuevo técnico"), "Ana Ficticia");
    await user.click(within(tecnicos).getByRole("button", { name: "Agregar técnico" }));
    await user.click(within(tecnicos).getByRole("button", { name: "Desactivar Diego Ficticio" }));

    await waitFor(() => expect(calls.filter((c) => c.method !== "GET")).toHaveLength(2));
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({ full_name: "Ana Ficticia" });
    expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({ is_active: false });
  });
});
