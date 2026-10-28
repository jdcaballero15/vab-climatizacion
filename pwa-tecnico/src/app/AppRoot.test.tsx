import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import { StrictMode } from "react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { notifySessionExpired } from "../features/auth/session";
import { getAccessToken, setAccessToken } from "../features/auth/token";
import type { Session } from "../features/auth/types";
import { AppRoot } from "./AppRoot";

const session: Session = {
  access_token: "a1",
  user: {
    id: "u1",
    email: "tecnico@ot-demo.com",
    full_name: "Juan Pérez",
    role: "technician",
    must_change_password: false,
  },
};

const noOrders = { crew: { name: "Escuadrilla 1" }, today: "2026-10-26", orders: [] };

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function renderApp({ strict = false } = {}) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const app = (
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <AppRoot />
      </MemoryRouter>
    </QueryClientProvider>
  );
  render(strict ? <StrictMode>{app}</StrictMode> : app);
  return client;
}

// Normaliza las dos formas en que se llama a fetch: con un Request (cliente de API)
// o con (url, init) (la renovación con la cookie).
function toRequest(input: Request | string, init?: RequestInit): Request {
  return input instanceof Request ? input : new Request(input, init);
}

function pathOf(request: Request) {
  return new URL(request.url).pathname;
}

// Sin cookie (la renovación da 401) hay que ingresar; el login devuelve la sesión y la
// lista del técnico es una escuadrilla sin órdenes.
function respond(request: Request) {
  const path = pathOf(request);
  if (path.endsWith("/auth/refresh")) {
    return json({ detail: { code: "invalid_refresh_token" } }, 401);
  }
  return path.endsWith("/tech/orders") ? json(noOrders) : json(session);
}

async function login() {
  await screen.findByRole("heading", { name: "OT Técnico" });
  await userEvent.type(screen.getByLabelText("Correo electrónico"), "tecnico@ot-demo.com");
  await userEvent.type(screen.getByLabelText("Contraseña"), "Secreta123");
  await userEvent.click(screen.getByRole("button", { name: "Iniciar sesión" }));
  await screen.findByRole("heading", { name: "Escuadrilla 1" });
}

beforeEach(() => {
  setAccessToken(null);
});

afterEach(() => vi.restoreAllMocks());

describe("AppRoot", () => {
  it("guarda el access token en memoria al iniciar sesión", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: Request | string, init?: RequestInit) => respond(toRequest(input, init))),
    );
    renderApp();

    await login();

    expect(getAccessToken()).toBe("a1");
  });

  // E01-07, criterio 1: con la cookie vigente, al abrir entra directo.
  it("al abrir recupera la sesión con la cookie y entra sin login", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: Request | string, init?: RequestInit) => {
        const request = toRequest(input, init);
        if (pathOf(request).endsWith("/auth/refresh")) {
          return json({ access_token: "a2", user: session.user });
        }
        return respond(request);
      }),
    );
    renderApp();

    expect(screen.getByRole("status")).toHaveTextContent("Cargando");
    expect(await screen.findByRole("heading", { name: "Escuadrilla 1" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Contraseña")).not.toBeInTheDocument();
    expect(getAccessToken()).toBe("a2");
  });

  // E01-07, criterio 2: sin cookie válida, muestra el login.
  it("al abrir sin cookie válida muestra el login", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: Request | string, init?: RequestInit) => respond(toRequest(input, init))),
    );
    renderApp();

    expect(await screen.findByRole("heading", { name: "OT Técnico" })).toBeInTheDocument();
    expect(getAccessToken()).toBeNull();
  });

  // Con StrictMode el efecto corre dos veces: una segunda renovación con la misma cookie
  // fallaría (el token ya rotó), así que tiene que pedirse una sola.
  it("al abrir pide una sola renovación aunque el efecto corra dos veces", async () => {
    let refreshCalls = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: Request | string, init?: RequestInit) => {
        const request = toRequest(input, init);
        if (pathOf(request).endsWith("/auth/refresh")) {
          refreshCalls += 1;
          return json({ access_token: "a2", user: session.user });
        }
        return respond(request);
      }),
    );
    renderApp({ strict: true });

    await screen.findByRole("heading", { name: "Escuadrilla 1" });
    expect(refreshCalls).toBe(1);
  });

  // Criterio 2 (E01-07, criterio 3): cerrar sesión le pide al servidor que revoque la
  // cookie, sin mandar el token, y limpia los datos locales.
  it("al cerrar sesión pide revocar la cookie y limpia los datos locales", async () => {
    const logoutBodies: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: Request | string, init?: RequestInit) => {
        const request = toRequest(input, init);
        if (pathOf(request).endsWith("/auth/logout")) {
          logoutBodies.push(await request.text());
          return new Response(null, { status: 204 });
        }
        return respond(request);
      }),
    );
    const client = renderApp();
    await login();
    client.setQueryData(["datos"], { algo: 1 });

    await userEvent.click(screen.getByRole("button", { name: "Cerrar sesión" }));

    expect(await screen.findByRole("heading", { name: "OT Técnico" })).toBeInTheDocument();
    await waitFor(() => expect(logoutBodies).toEqual([""]));
    await waitFor(() => expect(getAccessToken()).toBeNull());
    expect(client.getQueryData(["datos"])).toBeUndefined();
  });

  it("limpia los datos locales aunque falle la llamada de cierre", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: Request | string, init?: RequestInit) => {
        const request = toRequest(input, init);
        if (pathOf(request).endsWith("/auth/logout")) {
          throw new TypeError("sin conexión");
        }
        return respond(request);
      }),
    );
    renderApp();
    await login();

    await userEvent.click(screen.getByRole("button", { name: "Cerrar sesión" }));

    expect(await screen.findByRole("heading", { name: "OT Técnico" })).toBeInTheDocument();
    await waitFor(() => expect(getAccessToken()).toBeNull());
  });

  // Criterio 4: si el cliente no logra renovar la sesión, vuelve al login.
  it("vuelve al login cuando la sesión cae", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: Request | string, init?: RequestInit) => respond(toRequest(input, init))),
    );
    const client = renderApp();
    await login();
    client.setQueryData(["datos"], { algo: 1 });

    act(() => notifySessionExpired());

    expect(await screen.findByRole("heading", { name: "OT Técnico" })).toBeInTheDocument();
    expect(client.getQueryData(["datos"])).toBeUndefined();
  });

  // Alguien de la oficina que entra a la app del técnico no queda trabado en "Cargando":
  // se le avisa y puede cerrar la sesión, sin pedir la lista de órdenes (que daría 403).
  it("a un usuario que no es de escuadrilla le avisa y lo deja salir", async () => {
    const paths: string[] = [];
    const admin = { ...session, user: { ...session.user, role: "admin" as const } };
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: Request | string, init?: RequestInit) => {
        const request = toRequest(input, init);
        paths.push(pathOf(request));
        if (pathOf(request).endsWith("/auth/refresh")) {
          return json({ access_token: "a2", user: admin.user });
        }
        if (pathOf(request).endsWith("/auth/logout")) {
          return new Response(null, { status: 204 });
        }
        return respond(request);
      }),
    );
    renderApp();

    expect(
      await screen.findByRole("heading", { name: "Esta app es para las escuadrillas" }),
    ).toBeInTheDocument();
    expect(paths.some((path) => path.endsWith("/tech/orders"))).toBe(false);

    await userEvent.click(screen.getByRole("button", { name: "Cerrar sesión" }));

    expect(await screen.findByRole("heading", { name: "OT Técnico" })).toBeInTheDocument();
    await waitFor(() => expect(paths.some((path) => path.endsWith("/auth/logout"))).toBe(true));
    expect(getAccessToken()).toBeNull();
  });

  // E01-05, criterios 3 y 4: con una contraseña temporal, antes de seguir hay que elegir una nueva.
  describe("con una contraseña temporal", () => {
    function stubTemporary(passwordResponse: () => Response = () => json(session.user)) {
      const bodies: unknown[] = [];
      const temporal = { ...session, user: { ...session.user, must_change_password: true } };
      vi.stubGlobal(
        "fetch",
        vi.fn(async (input: Request | string, init?: RequestInit) => {
          const request = toRequest(input, init);
          if (pathOf(request).endsWith("/auth/refresh")) {
            return json(temporal);
          }
          if (pathOf(request).endsWith("/auth/password")) {
            bodies.push(await request.json());
            return passwordResponse();
          }
          return respond(request);
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

    it("pide elegir una nueva y después entra a sus órdenes", async () => {
      const bodies = stubTemporary();
      renderApp();

      expect(
        await screen.findByRole("heading", { name: "Elegí una contraseña nueva" }),
      ).toBeInTheDocument();

      await completar("TemporalDePrueba", "Nueva-clave-9");

      expect(await screen.findByRole("heading", { name: "Escuadrilla 1" })).toBeInTheDocument();
      expect(bodies).toEqual([
        { current_password: "TemporalDePrueba", new_password: "Nueva-clave-9" },
      ]);
    });

    it.each([
      ["corta", "corta", "corta", "Tiene que tener al menos 8 caracteres."],
      [
        "igual a la temporal",
        "TemporalDePrueba",
        "TemporalDePrueba",
        "Tiene que ser distinta de la temporal.",
      ],
      ["sin coincidir", "Nueva-clave-9", "Otra-clave-9", "Las dos contraseñas no coinciden."],
    ])("avisa y no la guarda si es %s", async (_caso, nueva, repetida, aviso) => {
      const bodies = stubTemporary();
      renderApp();

      await completar("TemporalDePrueba", nueva, repetida);

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
    });
  });
});
