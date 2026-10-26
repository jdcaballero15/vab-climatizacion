import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LoginPage } from "./LoginPage";
import type { Session } from "./types";

function renderLogin(onSuccess: (session: Session) => void = () => {}) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <LoginPage onSuccess={onSuccess} />
    </QueryClientProvider>,
  );
}

function mockFetch(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(JSON.stringify(body), {
          status,
          headers: { "Content-Type": "application/json" },
        }),
    ),
  );
}

afterEach(() => vi.restoreAllMocks());

describe("LoginPage", () => {
  it("muestra el formulario de inicio de sesión en español", () => {
    renderLogin();

    expect(screen.getByRole("heading", { name: "OT Técnico" })).toBeInTheDocument();
    expect(screen.getByLabelText("Correo electrónico")).toBeInTheDocument();
    expect(screen.getByLabelText("Contraseña")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Iniciar sesión" })).toBeInTheDocument();
  });

  it("muestra un mensaje genérico cuando las credenciales son incorrectas", async () => {
    mockFetch(401, { detail: { code: "invalid_credentials", message: "x" } });
    renderLogin();

    await userEvent.type(screen.getByLabelText("Correo electrónico"), "tecnico@ot-demo.com");
    await userEvent.type(screen.getByLabelText("Contraseña"), "incorrecta");
    await userEvent.click(screen.getByRole("button", { name: "Iniciar sesión" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Correo o contraseña incorrectos.");
  });

  it("entrega la sesión al iniciar sesión con éxito", async () => {
    const session: Session = {
      access_token: "token",
      refresh_token: "refresco",
      token_type: "bearer",
      user: {
        id: "u1",
        email: "tecnico@ot-demo.com",
        full_name: "Juan Pérez",
        role: "technician",
      },
    };
    mockFetch(200, session);
    const onSuccess = vi.fn();
    renderLogin(onSuccess);

    await userEvent.type(screen.getByLabelText("Correo electrónico"), "tecnico@ot-demo.com");
    await userEvent.type(screen.getByLabelText("Contraseña"), "Secreta123");
    await userEvent.click(screen.getByRole("button", { name: "Iniciar sesión" }));

    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
    expect(onSuccess.mock.calls[0][0]).toEqual(session);
  });
});
