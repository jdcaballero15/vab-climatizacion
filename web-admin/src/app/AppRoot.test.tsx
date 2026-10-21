import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppRoot } from "./AppRoot";

afterEach(() => vi.restoreAllMocks());

// Criterio 1: tras iniciar sesión, el usuario ve la pantalla de inicio de su rol.
describe("AppRoot", () => {
  it("después de iniciar sesión muestra la pantalla de inicio con el rol", async () => {
    const session = {
      access_token: "token",
      token_type: "bearer",
      user: { id: "u1", email: "ana@ot-demo.com", full_name: "Ana Gómez", role: "admin" },
    };
    const json = (body: unknown) =>
      new Response(JSON.stringify(body), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    vi.stubGlobal(
      "fetch",
      vi.fn(async (request: Request) =>
        request.url.includes("/admin/users") ? json([]) : json(session),
      ),
    );

    const client = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <AppRoot />
      </QueryClientProvider>,
    );

    await userEvent.type(screen.getByLabelText("Correo electrónico"), "ana@ot-demo.com");
    await userEvent.type(screen.getByLabelText("Contraseña"), "Secreta123");
    await userEvent.click(screen.getByRole("button", { name: "Iniciar sesión" }));

    expect(await screen.findByRole("heading", { name: "Hola, Ana Gómez" })).toBeInTheDocument();
    expect(screen.getByText("Ingresaste como Administración.")).toBeInTheDocument();
  });
});
