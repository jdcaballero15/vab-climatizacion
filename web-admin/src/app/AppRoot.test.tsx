import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppRoot } from "./AppRoot";

const session = {
  access_token: "token",
  refresh_token: "refresh",
  token_type: "bearer",
  user: { id: "u1", email: "ana@ot-demo.com", full_name: "Ana Gómez", role: "admin" },
};

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
      <AppRoot />
    </QueryClientProvider>,
  );
}

async function iniciarSesion() {
  await userEvent.type(screen.getByLabelText("Correo electrónico"), "ana@ot-demo.com");
  await userEvent.type(screen.getByLabelText("Contraseña"), "Secreta123");
  await userEvent.click(screen.getByRole("button", { name: "Iniciar sesión" }));
}

afterEach(() => vi.restoreAllMocks());

describe("AppRoot", () => {
  it("después de iniciar sesión muestra la pantalla de inicio con el rol", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (request: Request) =>
        request.url.includes("/admin/users") ? json([]) : json(session),
      ),
    );
    renderApp();

    await iniciarSesion();

    expect(await screen.findByRole("heading", { name: "Hola, Ana Gómez" })).toBeInTheDocument();
    expect(screen.getByText("Ingresaste como Administración.")).toBeInTheDocument();
  });

  // Criterio 2: al cerrar sesión se invalida el refresh token en el servidor y se
  // vuelve al login.
  it("al cerrar sesión llama a /auth/logout con el refresh token y vuelve al login", async () => {
    let logoutBody: unknown = null;
    const fetchMock = vi.fn(async (request: Request) => {
      const path = new URL(request.url).pathname;
      if (path.endsWith("/auth/logout")) {
        logoutBody = await request.clone().json();
        return new Response(null, { status: 204 });
      }
      if (path.endsWith("/admin/users")) {
        return json([]);
      }
      return json(session);
    });
    vi.stubGlobal("fetch", fetchMock);
    renderApp();

    await iniciarSesion();
    await screen.findByRole("heading", { name: "Hola, Ana Gómez" });

    await userEvent.click(screen.getByRole("button", { name: "Cerrar sesión" }));

    expect(await screen.findByLabelText("Correo electrónico")).toBeInTheDocument();
    await waitFor(() => expect(logoutBody).toEqual({ refresh_token: "refresh" }));
  });
});
