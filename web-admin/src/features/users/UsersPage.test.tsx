import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { UserAdmin } from "./types";
import { UsersPage } from "./UsersPage";

const EXISTENTE: UserAdmin = {
  id: "u1",
  email: "ana@ot-demo.com",
  full_name: "Ana Gómez",
  role: "admin",
  is_active: true,
  must_change_password: false,
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
      <MemoryRouter>
        <UsersPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe("UsersPage", () => {
  it("lista los usuarios existentes", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (request: Request) =>
        json(new URL(request.url).pathname.endsWith("/deactivated") ? [] : [EXISTENTE]),
      ),
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

  // E01-05, criterio 1: con confirmación, muestra la temporal una sola vez y se puede copiar.
  it("restablece la contraseña y muestra la temporal una sola vez", async () => {
    const user = userEvent.setup();
    const posts: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (request: Request) => {
        if (request.method === "POST") {
          posts.push(new URL(request.url).pathname);
          return json({ temporary_password: "TemporalDePrueba" });
        }
        return json([EXISTENTE]);
      }),
    );
    renderUsers();

    await user.click(await screen.findByRole("button", { name: "Restablecer contraseña" }));
    expect(screen.getByText(/se cierran todas sus sesiones/)).toBeInTheDocument();
    expect(posts).toEqual([]);

    await user.click(screen.getByRole("button", { name: "Confirmar restablecimiento" }));

    expect(await screen.findByText("TemporalDePrueba")).toBeInTheDocument();
    expect(posts).toEqual(["/api/admin/users/u1/password-reset"]);

    await user.click(screen.getByRole("button", { name: "Copiar" }));
    expect(await navigator.clipboard.readText()).toBe("TemporalDePrueba");
    expect(screen.getByRole("button", { name: "Copiada" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Listo" }));
    expect(screen.queryByText("TemporalDePrueba")).not.toBeInTheDocument();
  });

  it("sin confirmar no restablece nada", async () => {
    const fetchMock = vi.fn(async () => json([EXISTENTE]));
    vi.stubGlobal("fetch", fetchMock);
    renderUsers();

    await userEvent.click(await screen.findByRole("button", { name: "Restablecer contraseña" }));
    await userEvent.click(screen.getByRole("button", { name: "Volver" }));

    expect(screen.queryByText(/se cierran todas sus sesiones/)).not.toBeInTheDocument();
    const methods = fetchMock.mock.calls.map((call) => (call as unknown as [Request])[0].method);
    expect(methods).not.toContain("POST");
  });

  // E01-08: los dados de baja aparecen aparte y se reactivan desde ahí.
  it("lista los dados de baja y los reactiva", async () => {
    const user = userEvent.setup();
    const baja: UserAdmin = {
      id: "u2",
      email: "beto@ot-demo.com",
      full_name: "Beto Ficticio",
      role: "technician",
      is_active: false,
      must_change_password: false,
      deleted_at: "2026-11-20T15:00:00Z",
    };
    let reactivado = false;
    const posts: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (request: Request) => {
        const path = new URL(request.url).pathname;
        if (request.method === "POST") {
          posts.push(path);
          reactivado = true;
          return json({ ...baja, is_active: true, deleted_at: null });
        }
        if (path.endsWith("/deactivated")) {
          return json(reactivado ? [] : [baja]);
        }
        return json(
          reactivado ? [EXISTENTE, { ...baja, is_active: true, deleted_at: null }] : [EXISTENTE],
        );
      }),
    );
    renderUsers();

    const seccion = await screen.findByRole("region", { name: "Dados de baja" });
    expect(
      await within(seccion).findByRole("cell", { name: "beto@ot-demo.com" }),
    ).toBeInTheDocument();

    await user.click(within(seccion).getByRole("button", { name: "Reactivar" }));

    expect(posts).toEqual(["/api/admin/users/u2/reactivate"]);
    expect(await screen.findByText("No hay usuarios dados de baja.")).toBeInTheDocument();
    const activos = screen.getByRole("table", { name: "Usuarios activos" });
    expect(within(activos).getByRole("cell", { name: "beto@ot-demo.com" })).toBeInTheDocument();
  });
});
