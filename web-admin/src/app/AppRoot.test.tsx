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
    refresh_token: "refresh",
    token_type: "bearer",
    user: { id: "u1", email: "ana@ot-demo.com", full_name: NAMES[role], role },
  };
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/** Simula la API: el login devuelve la sesión del rol y los listados vienen vacíos. */
function stubApi(role: Role) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (request: Request) =>
      request.url.includes("/admin/") ? json([]) : json(sessionFor(role)),
    ),
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
  await userEvent.type(screen.getByLabelText("Correo electrónico"), "ana@ot-demo.com");
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

  // Criterio 2 de E01-02: al cerrar sesión se invalida el refresh token en el servidor y
  // se vuelve al login.
  it("al cerrar sesión llama a /auth/logout con el refresh token y vuelve al login", async () => {
    let logoutBody: unknown = null;
    const fetchMock = vi.fn(async (request: Request) => {
      const path = new URL(request.url).pathname;
      if (path.endsWith("/auth/logout")) {
        logoutBody = await request.clone().json();
        return new Response(null, { status: 204 });
      }
      if (path.includes("/admin/")) {
        return json([]);
      }
      return json(sessionFor("admin"));
    });
    vi.stubGlobal("fetch", fetchMock);
    renderApp("/clientes");

    await iniciarSesion();
    await screen.findByRole("heading", { name: "Clientes" });

    await userEvent.click(screen.getByRole("button", { name: "Cerrar sesión" }));

    expect(await screen.findByLabelText("Correo electrónico")).toBeInTheDocument();
    await waitFor(() => expect(logoutBody).toEqual({ refresh_token: "refresh" }));
    // El próximo usuario entra a su pantalla de inicio, no a la del anterior.
    expect(currentPath()).toBe("/");
  });
});
