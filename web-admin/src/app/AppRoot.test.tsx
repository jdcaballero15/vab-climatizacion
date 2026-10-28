import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppRoutes } from "./router";

type Role = "admin" | "owner" | "technician";

const NAMES: Record<Role, string> = {
  admin: "Ana Gómez",
  owner: "Diego Pérez",
  technician: "Tomás Ruiz",
};

function sessionFor(role: Role) {
  return {
    access_token: "token",
    user: {
      id: "u1",
      email: "ana@ot-demo.com",
      full_name: NAMES[role],
      role,
      must_change_password: false,
    },
  };
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

// Normaliza las dos formas en que se llama a fetch: con un Request (cliente de API)
// o con (url, init) (la renovación con la cookie).
function toRequest(input: Request | string, init?: RequestInit): Request {
  return input instanceof Request ? input : new Request(input, init);
}

/**
 * Simula la API: el login devuelve la sesión del rol y los listados vienen vacíos. Sin
 * `cookie`, la renovación al abrir da 401 y hay que ingresar; con `cookie`, recupera la sesión.
 */
function apiFor(role: Role, { cookie = false } = {}) {
  return async (request: Request) => {
    const path = new URL(request.url).pathname;
    if (path.endsWith("/auth/refresh")) {
      return cookie ? json(sessionFor(role)) : json({ detail: "sin sesión" }, 401);
    }
    return path.includes("/admin/") ? json([]) : json(sessionFor(role));
  };
}

function stubApi(role: Role, options: { cookie?: boolean } = {}) {
  const respond = apiFor(role, options);
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: Request | string, init?: RequestInit) => respond(toRequest(input, init))),
  );
}

/** Deja a la vista la dirección actual, para verificar a qué pantalla se navegó. */
function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{location.pathname}</output>;
}

function currentPath() {
  return screen.getByTestId("location").textContent;
}

function renderApp(initialPath = "/") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialPath]}>
        <AppRoutes />
        <LocationProbe />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function iniciarSesion() {
  await userEvent.type(await screen.findByLabelText("Correo electrónico"), "ana@ot-demo.com");
  await userEvent.type(screen.getByLabelText("Contraseña"), "Secreta123");
  await userEvent.click(screen.getByRole("button", { name: "Iniciar sesión" }));
}

function menu() {
  return screen.getByRole("navigation", { name: "Menú principal" });
}

afterEach(() => vi.restoreAllMocks());

describe("AppRoot", () => {
  it("después de iniciar sesión abre Órdenes y muestra el usuario con su rol", async () => {
    stubApi("admin");
    renderApp();

    await iniciarSesion();

    expect(await screen.findByRole("heading", { name: "Órdenes" })).toBeInTheDocument();
    expect(currentPath()).toBe("/ordenes");
    expect(within(menu()).getByText("Ana Gómez")).toBeInTheDocument();
    expect(within(menu()).getByText("Administración")).toBeInTheDocument();
  });

  it("cada sección es una pantalla aparte: al elegir otra en el menú, se reemplaza", async () => {
    stubApi("admin");
    renderApp();
    await iniciarSesion();
    await screen.findByRole("heading", { name: "Órdenes" });

    await userEvent.click(within(menu()).getByRole("link", { name: "Clientes" }));

    expect(await screen.findByRole("heading", { name: "Clientes" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Órdenes" })).not.toBeInTheDocument();
    expect(currentPath()).toBe("/clientes");
    expect(within(menu()).getByRole("link", { name: "Clientes" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("administración ve todas las secciones en el menú", async () => {
    stubApi("admin");
    renderApp();
    await iniciarSesion();
    await screen.findByRole("heading", { name: "Órdenes" });

    const links = within(menu())
      .getAllByRole("link")
      .map((link) => link.textContent);
    expect(links).toEqual([
      "Órdenes",
      "Clientes",
      "Escuadrillas",
      "Usuarios",
      "Tipos de trabajo",
      "Tipos de equipo",
      "Fallas",
      "Reparaciones",
    ]);
  });

  it("un link directo lleva a esa pantalla después del login", async () => {
    stubApi("admin");
    renderApp("/catalogos/fallas");

    await iniciarSesion();

    expect(await screen.findByRole("heading", { name: "Fallas" })).toBeInTheDocument();
    expect(currentPath()).toBe("/catalogos/fallas");
  });

  it("una dirección que no existe vuelve a la pantalla de inicio", async () => {
    stubApi("admin");
    renderApp("/no-existe");

    await iniciarSesion();

    expect(await screen.findByRole("heading", { name: "Órdenes" })).toBeInTheDocument();
    expect(currentPath()).toBe("/ordenes");
  });

  it("dirección solo ve Usuarios, y una sección de administración la devuelve ahí", async () => {
    stubApi("owner");
    renderApp("/clientes");

    await iniciarSesion();

    expect(await screen.findByRole("heading", { name: "Usuarios" })).toBeInTheDocument();
    expect(currentPath()).toBe("/usuarios");
    expect(screen.queryByRole("heading", { name: "Clientes" })).not.toBeInTheDocument();
    const links = within(menu())
      .getAllByRole("link")
      .map((link) => link.textContent);
    expect(links).toEqual(["Usuarios"]);
  });

  it("un rol sin secciones ve el saludo con su rol", async () => {
    stubApi("technician");
    renderApp();

    await iniciarSesion();

    expect(await screen.findByRole("heading", { name: "Hola, Tomás Ruiz" })).toBeInTheDocument();
    expect(screen.getByText("Ingresaste como Técnico.")).toBeInTheDocument();
    expect(within(menu()).queryAllByRole("link")).toHaveLength(0);
  });

  it("en pantallas chicas el botón Menú abre y cierra el menú", async () => {
    stubApi("admin");
    renderApp();
    await iniciarSesion();
    await screen.findByRole("heading", { name: "Órdenes" });
    const toggle = screen.getByRole("button", { name: "Menú" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");

    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");

    // Elegir una sección cierra el menú.
    await userEvent.click(within(menu()).getByRole("link", { name: "Fallas" }));
    expect(toggle).toHaveAttribute("aria-expanded", "false");
  });

  // E01-07, criterio 1: con la cookie vigente, recargar deja en la misma pantalla.
  it("al recargar con la cookie vigente entra directo a la misma pantalla", async () => {
    stubApi("admin", { cookie: true });
    renderApp("/clientes");

    expect(screen.getByText("Cargando…")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Clientes" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Contraseña")).not.toBeInTheDocument();
    expect(currentPath()).toBe("/clientes");
  });

  // E01-07, criterio 2: sin cookie válida, muestra el login.
  it("al abrir sin cookie válida muestra el login", async () => {
    stubApi("admin");
    renderApp("/clientes");

    expect(await screen.findByLabelText("Correo electrónico")).toBeInTheDocument();
  });

  // Criterio 2 de E01-02 (E01-07, criterio 3): al cerrar sesión el servidor revoca la
  // cookie (no se manda ningún token) y se vuelve al login.
  it("al cerrar sesión llama a /auth/logout sin token y vuelve al login", async () => {
    let logoutBody: string | null = null;
    const respond = apiFor("admin");
    const fetchMock = vi.fn(async (input: Request | string, init?: RequestInit) => {
      const request = toRequest(input, init);
      if (new URL(request.url).pathname.endsWith("/auth/logout")) {
        logoutBody = await request.text();
        return new Response(null, { status: 204 });
      }
      return respond(request);
    });
    vi.stubGlobal("fetch", fetchMock);
    renderApp("/clientes");

    await iniciarSesion();
    await screen.findByRole("heading", { name: "Clientes" });

    await userEvent.click(screen.getByRole("button", { name: "Cerrar sesión" }));

    expect(await screen.findByLabelText("Correo electrónico")).toBeInTheDocument();
    await waitFor(() => expect(logoutBody).toBe(""));
    // El próximo usuario entra a su pantalla de inicio, no a la del anterior.
    expect(currentPath()).toBe("/");
  });

  // E01-05, criterios 3 y 4: con una contraseña temporal, antes de seguir hay que elegir una nueva.
  describe("con una contraseña temporal", () => {
    function stubTemporary(
      passwordResponse: () => Response = () => json(sessionFor("admin").user),
    ) {
      const bodies: unknown[] = [];
      const temporal = {
        ...sessionFor("admin"),
        user: { ...sessionFor("admin").user, must_change_password: true },
      };
      vi.stubGlobal(
        "fetch",
        vi.fn(async (input: Request | string, init?: RequestInit) => {
          const request = toRequest(input, init);
          const path = new URL(request.url).pathname;
          if (path.endsWith("/auth/refresh")) {
            return json(temporal);
          }
          if (path.endsWith("/auth/password")) {
            bodies.push(await request.json());
            return passwordResponse();
          }
          return path.includes("/admin/") ? json([]) : json(temporal);
        }),
      );
      return bodies;
    }

    async function completar(actual: string, nueva: string, repetida = nueva) {
      await userEvent.type(await screen.findByLabelText("Contraseña temporal"), actual);
      await userEvent.type(screen.getByLabelText("Contraseña nueva"), nueva);
      await userEvent.type(screen.getByLabelText("Repetir la contraseña nueva"), repetida);
      await userEvent.click(screen.getByRole("button", { name: "Guardar y entrar" }));
    }

    it("pide elegir una nueva y después entra", async () => {
      const bodies = stubTemporary();
      renderApp();

      expect(
        await screen.findByRole("heading", { name: "Elegí una contraseña nueva" }),
      ).toBeInTheDocument();
      expect(screen.queryByRole("navigation", { name: "Menú principal" })).not.toBeInTheDocument();

      await completar("TemporalDePrueba", "Nueva-clave-9");

      expect(await screen.findByRole("heading", { name: "Órdenes" })).toBeInTheDocument();
      expect(bodies).toEqual([
        { current_password: "TemporalDePrueba", new_password: "Nueva-clave-9" },
      ]);
    });

    it.each([
      ["corta", "corta", "Tiene que tener al menos 8 caracteres."],
      ["igual a la temporal", "TemporalDePrueba", "Tiene que ser distinta de la temporal."],
      ["sin coincidir", "Nueva-clave-9", "Las dos contraseñas no coinciden."],
    ])("avisa y no la guarda si es %s", async (_caso, nueva, aviso) => {
      const bodies = stubTemporary();
      renderApp();

      await completar(
        "TemporalDePrueba",
        nueva,
        nueva === "Nueva-clave-9" ? "Otra-clave-9" : nueva,
      );

      expect(await screen.findByText(aviso)).toBeInTheDocument();
      expect(bodies).toEqual([]);
    });

    it("avisa si la temporal no es correcta", async () => {
      stubTemporary(() =>
        json({ detail: { code: "invalid_current_password", message: "x" } }, 422),
      );
      renderApp();

      await completar("equivocada", "Nueva-clave-9");

      expect(await screen.findByText("La contraseña temporal no es correcta.")).toBeInTheDocument();
      expect(
        screen.getByRole("heading", { name: "Elegí una contraseña nueva" }),
      ).toBeInTheDocument();
    });
  });

  // E01-05: restablecerse la propia contraseña no deja la sesión con errores 403.
  describe("restablecerse la propia contraseña", () => {
    const PASSWORD_CHANGE_REQUIRED = () =>
      json(
        { detail: { code: "password_change_required", message: "Elegí una contraseña nueva." } },
        403,
      );

    function stubSelfReset() {
      let reset = false;
      const listados: string[] = [];
      vi.stubGlobal(
        "fetch",
        vi.fn(async (input: Request | string, init?: RequestInit) => {
          const request = toRequest(input, init);
          const path = new URL(request.url).pathname;
          if (path.endsWith("/auth/refresh")) {
            return json(sessionFor("admin"));
          }
          if (path.endsWith("/password-reset")) {
            reset = true;
            return json({ temporary_password: "TemporalDePrueba" });
          }
          if (path.endsWith("/admin/users")) {
            listados.push(path);
            return reset
              ? PASSWORD_CHANGE_REQUIRED()
              : json([{ ...sessionFor("admin").user, is_active: true }]);
          }
          return path.includes("/admin/") ? json([]) : json(sessionFor("admin"));
        }),
      );
      return listados;
    }

    it("muestra la temporal y al tocar Listo pide elegir una nueva", async () => {
      const user = userEvent.setup();
      const listados = stubSelfReset();
      renderApp("/usuarios");

      await user.click(await screen.findByRole("button", { name: "Restablecer contraseña" }));
      expect(screen.getByText(/Es tu propio usuario/)).toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: "Confirmar restablecimiento" }));

      expect(await screen.findByText("TemporalDePrueba")).toBeInTheDocument();
      expect(screen.getByText(/Tu contraseña temporal/)).toBeInTheDocument();
      // La lista no se recarga: la API ya la negaría y se perdería la temporal.
      expect(listados).toHaveLength(1);

      await user.click(screen.getByRole("button", { name: "Listo" }));

      expect(
        await screen.findByRole("heading", { name: "Elegí una contraseña nueva" }),
      ).toBeInTheDocument();
    });

    it("si la API pide una contraseña nueva en medio del uso, muestra la pantalla", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn(async (input: Request | string, init?: RequestInit) => {
          const request = toRequest(input, init);
          const path = new URL(request.url).pathname;
          if (path.endsWith("/auth/refresh")) {
            return json(sessionFor("admin"));
          }
          return path.includes("/admin/") ? PASSWORD_CHANGE_REQUIRED() : json(sessionFor("admin"));
        }),
      );
      renderApp("/usuarios");

      expect(
        await screen.findByRole("heading", { name: "Elegí una contraseña nueva" }),
      ).toBeInTheDocument();
    });
  });
});
