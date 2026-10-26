import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { notifySessionExpired } from "../features/auth/session";
import {
  getAccessToken,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
} from "../features/auth/token";
import type { Session } from "../features/auth/types";
import { AppRoot } from "./AppRoot";

const session: Session = {
  access_token: "a1",
  refresh_token: "r1",
  token_type: "bearer",
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

function renderApp() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <AppRoot />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return client;
}

// Login y sesión devuelven la sesión; la lista del técnico, una escuadrilla sin órdenes.
function respond(request: Request) {
  return new URL(request.url).pathname.endsWith("/tech/orders") ? json(noOrders) : json(session);
}

async function login() {
  await userEvent.type(screen.getByLabelText("Correo electrónico"), "tecnico@ot-demo.com");
  await userEvent.type(screen.getByLabelText("Contraseña"), "Secreta123");
  await userEvent.click(screen.getByRole("button", { name: "Iniciar sesión" }));
  await screen.findByRole("heading", { name: "Escuadrilla 1" });
}

beforeEach(() => {
  setAccessToken(null);
  setRefreshToken(null);
});

afterEach(() => vi.restoreAllMocks());

describe("AppRoot", () => {
  it("guarda los tokens en memoria al iniciar sesión", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (request: Request) => respond(request)),
    );
    renderApp();

    await login();

    expect(getAccessToken()).toBe("a1");
    expect(getRefreshToken()).toBe("r1");
  });

  // Criterio 2: cerrar sesión invalida el refresh token y limpia los datos locales.
  it("al cerrar sesión invalida el refresh token y limpia los datos locales", async () => {
    const logoutBodies: unknown[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (request: Request) => {
        if (new URL(request.url).pathname.endsWith("/auth/logout")) {
          logoutBodies.push(await request.json());
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
    await waitFor(() => expect(logoutBodies).toEqual([{ refresh_token: "r1" }]));
    await waitFor(() => expect(getRefreshToken()).toBeNull());
    expect(getAccessToken()).toBeNull();
    expect(client.getQueryData(["datos"])).toBeUndefined();
  });

  it("limpia los datos locales aunque falle la llamada de cierre", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (request: Request) => {
        if (new URL(request.url).pathname.endsWith("/auth/logout")) {
          throw new TypeError("sin conexión");
        }
        return respond(request);
      }),
    );
    renderApp();
    await login();

    await userEvent.click(screen.getByRole("button", { name: "Cerrar sesión" }));

    expect(await screen.findByRole("heading", { name: "OT Técnico" })).toBeInTheDocument();
    await waitFor(() => expect(getRefreshToken()).toBeNull());
    expect(getAccessToken()).toBeNull();
  });

  // Criterio 4: si el cliente no logra renovar la sesión, vuelve al login.
  it("vuelve al login cuando la sesión cae", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (request: Request) => respond(request)),
    );
    const client = renderApp();
    await login();
    client.setQueryData(["datos"], { algo: 1 });

    notifySessionExpired();

    expect(await screen.findByRole("heading", { name: "OT Técnico" })).toBeInTheDocument();
    expect(client.getQueryData(["datos"])).toBeUndefined();
  });
});
