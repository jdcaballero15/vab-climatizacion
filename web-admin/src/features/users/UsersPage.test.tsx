import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { UserAdmin } from "./types";
import { UsersPage } from "./UsersPage";

const EXISTENTE: UserAdmin = {
  id: "u1",
  email: "ana@ot-demo.com",
  full_name: "Ana Gómez",
  role: "admin",
  is_active: true,
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function renderUsers() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <UsersPage />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe("UsersPage", () => {
  it("lista los usuarios existentes", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => json([EXISTENTE])),
    );
    renderUsers();

    expect(await screen.findByRole("cell", { name: "ana@ot-demo.com" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Ana Gómez" })).toBeInTheDocument();
  });

  it("muestra un error claro si el correo ya existe", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (request: Request) => {
        if (request.method === "POST") {
          return json({ detail: { code: "email_already_exists", message: "x" } }, 409);
        }
        return json([EXISTENTE]);
      }),
    );
    renderUsers();

    await userEvent.type(screen.getByLabelText("Nombre"), "Otra Persona");
    await userEvent.type(screen.getByLabelText("Correo electrónico"), "ana@ot-demo.com");
    await userEvent.type(screen.getByLabelText("Contraseña inicial"), "Secreta123");
    await userEvent.click(screen.getByRole("button", { name: "Crear usuario" }));

    expect(await screen.findByText("Ya existe un usuario con ese correo.")).toBeInTheDocument();
  });
});
