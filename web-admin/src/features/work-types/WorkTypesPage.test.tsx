import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Task, WorkType } from "./types";
import { WorkTypesPage } from "./WorkTypesPage";

const SERVICE: WorkType = {
  id: "wt1",
  name: "Service",
  requires_failure_repair: false,
  is_active: true,
};
const RETIRO: WorkType = {
  id: "wt2",
  name: "Retiro",
  requires_failure_repair: false,
  is_active: false,
};
const LIMPIEZA: Task = { id: "t1", work_type_id: "wt1", name: "Limpieza", is_active: true };

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

interface Call {
  method: string;
  path: string;
  query: string;
  body: unknown;
}

/** Simula la API del catálogo y registra cada llamada. */
function stubApi(handler?: (call: Call) => Response | undefined) {
  const calls: Call[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (request: Request) => {
      const url = new URL(request.url);
      const body = request.method === "GET" ? null : await request.clone().json();
      const call = { method: request.method, path: url.pathname, query: url.search, body };
      calls.push(call);
      const custom = handler?.(call);
      if (custom) {
        return custom;
      }
      if (call.path.endsWith("/tasks")) {
        return json([LIMPIEZA]);
      }
      const includeInactive = call.query.includes("include_inactive=true");
      return json(includeInactive ? [RETIRO, SERVICE] : [SERVICE]);
    }),
  );
  return calls;
}

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <WorkTypesPage />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe("WorkTypesPage", () => {
  it("lista los tipos activos y muestra los desactivados al pedirlo", async () => {
    stubApi();
    renderPage();

    expect(await screen.findByText("Service")).toBeInTheDocument();
    expect(screen.queryByText("Retiro")).not.toBeInTheDocument();

    await userEvent.click(screen.getByLabelText("Mostrar desactivados"));

    expect(await screen.findByText("Retiro")).toBeInTheDocument();
    expect(screen.getByText("Desactivado")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reactivar Retiro" })).toBeInTheDocument();
  });

  it("crea un tipo de trabajo", async () => {
    const calls = stubApi((call) =>
      call.method === "POST"
        ? json(
            { id: "wt3", name: "Relevamiento", requires_failure_repair: false, is_active: true },
            201,
          )
        : undefined,
    );
    renderPage();
    await screen.findByText("Service");

    await userEvent.type(screen.getByLabelText("Nuevo tipo de trabajo"), "Relevamiento");
    await userEvent.click(screen.getByRole("button", { name: "Agregar tipo" }));

    await waitFor(() =>
      expect(calls).toContainEqual(
        expect.objectContaining({
          method: "POST",
          path: "/api/admin/work-types",
          body: { name: "Relevamiento" },
        }),
      ),
    );
  });

  it("muestra un error claro si el nombre ya existe", async () => {
    stubApi((call) =>
      call.method === "POST"
        ? json({ detail: { code: "work_type_name_already_exists", message: "x" } }, 409)
        : undefined,
    );
    renderPage();
    await screen.findByText("Service");

    await userEvent.type(screen.getByLabelText("Nuevo tipo de trabajo"), "service");
    await userEvent.click(screen.getByRole("button", { name: "Agregar tipo" }));

    expect(
      await screen.findByText(
        "Ya existe un tipo de trabajo con ese nombre (puede estar desactivado).",
      ),
    ).toBeInTheDocument();
  });

  it("renombra y desactiva un tipo de trabajo", async () => {
    const calls = stubApi((call) =>
      call.method === "PATCH" ? json({ ...SERVICE, ...(call.body as object) }) : undefined,
    );
    renderPage();
    await screen.findByText("Service");

    await userEvent.click(screen.getByRole("button", { name: "Renombrar Service" }));
    const input = screen.getByLabelText("Nombre nuevo");
    await userEvent.clear(input);
    await userEvent.type(input, "Mantenimiento");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await userEvent.click(await screen.findByRole("button", { name: "Desactivar Service" }));

    await waitFor(() => {
      const patches = calls.filter((call) => call.method === "PATCH");
      expect(patches.map((call) => call.body)).toEqual([
        { name: "Mantenimiento" },
        { is_active: false },
      ]);
      expect(patches[0].path).toBe("/api/admin/work-types/wt1");
    });
  });

  it("muestra las subtareas de un tipo y agrega una", async () => {
    const calls = stubApi((call) =>
      call.method === "POST"
        ? json({ id: "t2", work_type_id: "wt1", name: "Carga de gas", is_active: true }, 201)
        : undefined,
    );
    renderPage();
    await screen.findByText("Service");

    await userEvent.click(screen.getByRole("button", { name: "Subtareas de Service" }));
    expect(await screen.findByText("Limpieza")).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Nueva subtarea"), "Carga de gas");
    await userEvent.click(screen.getByRole("button", { name: "Agregar subtarea" }));

    await waitFor(() =>
      expect(calls).toContainEqual(
        expect.objectContaining({
          method: "POST",
          path: "/api/admin/work-types/wt1/tasks",
          body: { name: "Carga de gas" },
        }),
      ),
    );
  });

  it("desactiva una subtarea", async () => {
    const calls = stubApi((call) =>
      call.method === "PATCH" ? json({ ...LIMPIEZA, is_active: false }) : undefined,
    );
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Subtareas de Service" }));

    await userEvent.click(await screen.findByRole("button", { name: "Desactivar Limpieza" }));

    await waitFor(() =>
      expect(calls).toContainEqual(
        expect.objectContaining({
          method: "PATCH",
          path: "/api/admin/work-types/wt1/tasks/t1",
          body: { is_active: false },
        }),
      ),
    );
  });

  // E02-10, criterio 1: marcar que un tipo pide falla y reparación al cerrar.
  it("marca que un tipo de trabajo pide falla y reparación", async () => {
    const calls = stubApi((call) =>
      call.method === "PATCH" ? json({ ...SERVICE, requires_failure_repair: true }) : undefined,
    );
    renderPage();

    const casilla = await screen.findByRole("checkbox", {
      name: "Service pide falla y reparación",
    });
    expect(casilla).not.toBeChecked();

    await userEvent.click(casilla);

    await waitFor(() =>
      expect(calls.find((call) => call.method === "PATCH")).toMatchObject({
        path: "/api/admin/work-types/wt1",
        body: { requires_failure_repair: true },
      }),
    );
  });

  it("muestra marcado un tipo que ya pide falla y reparación", async () => {
    stubApi((call) =>
      call.method === "GET" && !call.path.endsWith("/tasks")
        ? json([{ ...SERVICE, requires_failure_repair: true }])
        : undefined,
    );
    renderPage();

    expect(
      await screen.findByRole("checkbox", { name: "Service pide falla y reparación" }),
    ).toBeChecked();
  });
});
