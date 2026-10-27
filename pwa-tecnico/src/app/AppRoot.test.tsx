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
});
