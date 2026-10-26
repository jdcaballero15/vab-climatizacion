import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EquipmentTypesPage } from "../equipment-types/EquipmentTypesPage";
import type { EquipmentType } from "../equipment-types/types";
import { FailuresPage } from "./FailuresPage";
import type { Failure } from "./types";

const SPLIT: EquipmentType = { id: "et1", name: "Split", is_active: true };
const FREEZER: EquipmentType = { id: "et2", name: "Freezer", is_active: false };
const NO_ENCIENDE: Failure = {
  id: "f1",
  equipment_type_id: null,
  name: "No enciende",
  is_active: true,
};
const PIERDE_AGUA: Failure = {
  id: "f2",
  equipment_type_id: "et1",
  name: "Pierde agua",
  is_active: true,
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

interface Call {
  method: string;
  path: string;
  params: URLSearchParams;
  body: unknown;
}

/** Simula la API: tipos de equipo y fallas. Registra cada llamada. */
function stubApi(handler?: (call: Call) => Response | undefined) {
  const calls: Call[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (request: Request) => {
      const url = new URL(request.url);
      const body = request.method === "GET" ? null : await request.clone().json();
      const call = { method: request.method, path: url.pathname, params: url.searchParams, body };
      calls.push(call);
      const custom = handler?.(call);
      if (custom) {
        return custom;
      }
      if (call.path.endsWith("/equipment-types")) {
        return json([FREEZER, SPLIT]);
      }
      // Sin tipo, la API devuelve todas; con el Split, las suyas más las genéricas. En los
      // dos casos son estas dos, y la pantalla decide qué mostrar.
      return json([NO_ENCIENDE, PIERDE_AGUA]);
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
      <FailuresPage />
    </QueryClientProvider>,
  );
}

function failuresList() {
  return within(screen.getByRole("list", { name: "Fallas" }));
}

afterEach(() => vi.restoreAllMocks());

describe("FailuresPage", () => {
  it("arranca en genéricas y muestra solo las fallas sin tipo", async () => {
    stubApi();
    renderPage();

    expect(await screen.findByText("No enciende")).toBeInTheDocument();
    expect(screen.queryByText("Pierde agua")).not.toBeInTheDocument();
  });

  it("ofrece todos los tipos de equipo y marca los desactivados", async () => {
    stubApi();
    renderPage();

    const selector = await screen.findByLabelText("Tipo de equipo");
    await waitFor(() =>
      expect(
        within(selector)
          .getAllByRole("option")
          .map((option) => option.textContent),
      ).toEqual(["Genéricas", "Freezer (desactivado)", "Split"]),
    );
  });

  it("al elegir un tipo muestra sus fallas y las genéricas marcadas", async () => {
    const calls = stubApi();
    renderPage();
    await screen.findByText("No enciende");

    await userEvent.selectOptions(screen.getByLabelText("Tipo de equipo"), "et1");

    expect(await screen.findByText("Pierde agua")).toBeInTheDocument();
    expect(failuresList().getByText("Genérica")).toBeInTheDocument();
    expect(
      calls.some(
        (call) =>
          call.path === "/api/admin/failures" && call.params.get("equipment_type_id") === "et1",
      ),
    ).toBe(true);
  });

  it("crea una falla del tipo elegido", async () => {
    const calls = stubApi((call) =>
      call.method === "POST"
        ? json({ id: "f3", equipment_type_id: "et1", name: "Ruido", is_active: true }, 201)
        : undefined,
    );
    renderPage();
    await screen.findByText("No enciende");
    await userEvent.selectOptions(screen.getByLabelText("Tipo de equipo"), "et1");

    await userEvent.type(screen.getByLabelText("Nueva falla"), "Ruido");
    await userEvent.click(screen.getByRole("button", { name: "Agregar falla" }));

    await waitFor(() =>
      expect(calls).toContainEqual(
        expect.objectContaining({
          method: "POST",
          path: "/api/admin/failures",
          body: { name: "Ruido", equipment_type_id: "et1" },
        }),
      ),
    );
  });

  it("crea una falla genérica", async () => {
    const calls = stubApi((call) =>
      call.method === "POST"
        ? json({ id: "f3", equipment_type_id: null, name: "Ruido", is_active: true }, 201)
        : undefined,
    );
    renderPage();
    await screen.findByText("No enciende");

    await userEvent.type(screen.getByLabelText("Nueva falla"), "Ruido");
    await userEvent.click(screen.getByRole("button", { name: "Agregar falla" }));

    await waitFor(() =>
      expect(calls).toContainEqual(
        expect.objectContaining({
          method: "POST",
          body: { name: "Ruido", equipment_type_id: null },
        }),
      ),
    );
  });

  it("muestra un error claro si el nombre ya existe", async () => {
    stubApi((call) =>
      call.method === "POST"
        ? json({ detail: { code: "failure_name_already_exists", message: "x" } }, 409)
        : undefined,
    );
    renderPage();
    await screen.findByText("No enciende");

    await userEvent.type(screen.getByLabelText("Nueva falla"), "no enciende");
    await userEvent.click(screen.getByRole("button", { name: "Agregar falla" }));

    expect(
      await screen.findByText(
        "Ya existe una falla con ese nombre para ese tipo de equipo o como genérica (puede estar desactivada).",
      ),
    ).toBeInTheDocument();
  });

  it("renombra y desactiva una falla", async () => {
    const calls = stubApi((call) =>
      call.method === "PATCH" ? json({ ...NO_ENCIENDE, ...(call.body as object) }) : undefined,
    );
    renderPage();
    await screen.findByText("No enciende");

    await userEvent.click(screen.getByRole("button", { name: "Renombrar No enciende" }));
    const input = screen.getByLabelText("Nombre nuevo");
    await userEvent.clear(input);
    await userEvent.type(input, "No arranca");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await userEvent.click(await screen.findByRole("button", { name: "Desactivar No enciende" }));

    await waitFor(() => {
      const patches = calls.filter((call) => call.method === "PATCH");
      expect(patches.map((call) => call.body)).toEqual([
        { name: "No arranca" },
        { is_active: false },
      ]);
      expect(patches[0].path).toBe("/api/admin/failures/f1");
    });
  });

  it("pide las desactivadas al marcar mostrar desactivadas", async () => {
    const calls = stubApi();
    renderPage();
    await screen.findByText("No enciende");

    await userEvent.click(screen.getByLabelText("Mostrar desactivadas"));

    await waitFor(() =>
      expect(
        calls.some(
          (call) =>
            call.path === "/api/admin/failures" && call.params.get("include_inactive") === "true",
        ),
      ).toBe(true),
    );
  });

  it("al desactivar un tipo de equipo deja de mostrar sus fallas propias", async () => {
    // El backend real: con el tipo desactivado, solo devuelve las genéricas (criterio 5).
    let splitActive = true;
    stubApi((call) => {
      if (call.method === "PATCH" && call.path === "/api/admin/equipment-types/et1") {
        splitActive = false;
        return json({ ...SPLIT, is_active: false });
      }
      if (call.path.endsWith("/equipment-types")) {
        const split = { ...SPLIT, is_active: splitActive };
        const includeInactive = call.params.get("include_inactive") === "true";
        return json(includeInactive || splitActive ? [FREEZER, split] : []);
      }
      if (call.params.get("equipment_type_id") === "et1") {
        return json(splitActive ? [NO_ENCIENDE, PIERDE_AGUA] : [NO_ENCIENDE]);
      }
      return undefined;
    });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <EquipmentTypesPage />
        <FailuresPage />
      </QueryClientProvider>,
    );
    await screen.findByText("No enciende");
    await userEvent.selectOptions(screen.getByLabelText("Tipo de equipo"), "et1");
    expect(await screen.findByText("Pierde agua")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Desactivar Split" }));

    await waitFor(() => expect(screen.queryByText("Pierde agua")).not.toBeInTheDocument());
    expect(failuresList().getByText("No enciende")).toBeInTheDocument();
  });
});
