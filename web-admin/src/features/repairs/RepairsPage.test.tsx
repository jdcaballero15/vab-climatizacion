import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { EquipmentType } from "../equipment-types/types";
import { FailuresPage } from "../failures/FailuresPage";
import type { Failure } from "../failures/types";
import { RepairsPage } from "./RepairsPage";
import type { Repair } from "./types";

const AIRE: EquipmentType = { id: "et1", name: "Aire acondicionado", is_active: true };
const FREEZER: EquipmentType = { id: "et2", name: "Freezer", is_active: true };
const GAS: Failure = {
  id: "f1",
  equipment_type_id: null,
  name: "Falla del sistema de gas",
  is_active: true,
};
const ELECTRICA: Failure = {
  id: "f2",
  equipment_type_id: null,
  name: "Falla eléctrica o mecánica",
  is_active: true,
};
const NO_CONGELA: Failure = {
  id: "f3",
  equipment_type_id: "et2",
  name: "No congela",
  is_active: true,
};
const FILTRO: Repair = {
  id: "r1",
  failure_id: "f1",
  equipment_type_id: null,
  name: "Cambio de filtro de gas",
  is_active: true,
};
const INVERSORA: Repair = {
  id: "r2",
  failure_id: "f1",
  equipment_type_id: "et1",
  name: "Cambio de válvula inversora",
  is_active: true,
};
const CAPACITOR: Repair = {
  id: "r3",
  failure_id: "f2",
  equipment_type_id: null,
  name: "Cambio de capacitor",
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

/** Simula la API: tipos de equipo, fallas y reparaciones, filtrando como el backend. */
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
      const typeId = call.params.get("equipment_type_id");
      const ofType = <T extends { equipment_type_id: string | null }>(items: T[]) =>
        typeId
          ? items.filter((i) => i.equipment_type_id === null || i.equipment_type_id === typeId)
          : items;
      if (call.path.endsWith("/equipment-types")) {
        return json([AIRE, FREEZER]);
      }
      if (call.path.endsWith("/failures")) {
        return json(ofType([GAS, ELECTRICA, NO_CONGELA]));
      }
      const failureId = call.params.get("failure_id");
      const repairs = ofType([FILTRO, INVERSORA, CAPACITOR]);
      return json(failureId ? repairs.filter((r) => r.failure_id === failureId) : repairs);
    }),
  );
  return calls;
}

function renderPages(...pages: JSX.Element[]) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{pages}</QueryClientProvider>);
}

function repairsList() {
  return within(screen.getByRole("list", { name: "Reparaciones" }));
}

function selector(name: string) {
  return within(screen.getByRole("region", { name: "Reparaciones" })).getByLabelText(name);
}

afterEach(() => vi.restoreAllMocks());

describe("RepairsPage", () => {
  it("arranca en genéricas, con todas las fallas, y muestra la falla de cada reparación", async () => {
    stubApi();
    renderPages(<RepairsPage key="r" />);

    expect(await screen.findByText("Cambio de filtro de gas")).toBeInTheDocument();
    expect(screen.getByText("Cambio de capacitor")).toBeInTheDocument();
    expect(screen.queryByText("Cambio de válvula inversora")).not.toBeInTheDocument();
    expect(repairsList().getByText("Falla del sistema de gas")).toBeInTheDocument();
    expect(repairsList().getByText("Falla eléctrica o mecánica")).toBeInTheDocument();
  });

  it("filtra por falla", async () => {
    const calls = stubApi();
    renderPages(<RepairsPage key="r" />);
    await screen.findByText("Cambio de capacitor");

    await userEvent.selectOptions(selector("Falla"), "f2");

    await waitFor(() =>
      expect(screen.queryByText("Cambio de filtro de gas")).not.toBeInTheDocument(),
    );
    expect(screen.getByText("Cambio de capacitor")).toBeInTheDocument();
    expect(
      calls.some(
        (call) => call.path === "/api/admin/repairs" && call.params.get("failure_id") === "f2",
      ),
    ).toBe(true);
  });

  it("solo ofrece las fallas que aplican al tipo elegido", async () => {
    stubApi();
    renderPages(<RepairsPage key="r" />);
    await screen.findByText("Cambio de capacitor");

    const fallas = () =>
      within(selector("Falla"))
        .getAllByRole("option")
        .map((o) => o.textContent);
    await waitFor(() =>
      expect(fallas()).toEqual(["Todas", "Falla del sistema de gas", "Falla eléctrica o mecánica"]),
    );

    await userEvent.selectOptions(selector("Tipo de equipo"), "et2");
    await waitFor(() =>
      expect(fallas()).toEqual([
        "Todas",
        "Falla del sistema de gas",
        "Falla eléctrica o mecánica",
        "No congela",
      ]),
    );
  });

  it("pide elegir una falla antes de agregar", async () => {
    stubApi();
    renderPages(<RepairsPage key="r" />);
    await screen.findByText("Cambio de capacitor");

    expect(screen.getByText("Elegí una falla para agregar reparaciones.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Nueva reparación")).not.toBeInTheDocument();
  });

  it("crea una reparación de la falla y el tipo elegidos", async () => {
    const calls = stubApi((call) =>
      call.method === "POST"
        ? json({ ...INVERSORA, id: "r9", name: "Cambio de turbina" }, 201)
        : undefined,
    );
    renderPages(<RepairsPage key="r" />);
    await screen.findByText("Cambio de capacitor");

    await userEvent.selectOptions(selector("Tipo de equipo"), "et1");
    await userEvent.selectOptions(selector("Falla"), "f2");
    await userEvent.type(screen.getByLabelText("Nueva reparación"), "Cambio de turbina");
    await userEvent.click(screen.getByRole("button", { name: "Agregar reparación" }));

    await waitFor(() =>
      expect(calls).toContainEqual(
        expect.objectContaining({
          method: "POST",
          path: "/api/admin/repairs",
          body: { name: "Cambio de turbina", equipment_type_id: "et1", failure_id: "f2" },
        }),
      ),
    );
  });

  it("muestra un error claro si el nombre ya existe", async () => {
    stubApi((call) =>
      call.method === "POST"
        ? json({ detail: { code: "repair_name_already_exists", message: "x" } }, 409)
        : undefined,
    );
    renderPages(<RepairsPage key="r" />);
    await screen.findByText("Cambio de capacitor");

    await userEvent.selectOptions(selector("Falla"), "f2");
    await userEvent.type(screen.getByLabelText("Nueva reparación"), "cambio de capacitor");
    await userEvent.click(screen.getByRole("button", { name: "Agregar reparación" }));

    expect(
      await screen.findByText(
        "Ya existe una reparación con ese nombre para ese tipo de equipo o como genérica (puede estar desactivada).",
      ),
    ).toBeInTheDocument();
  });

  it("renombra y desactiva una reparación", async () => {
    const calls = stubApi((call) =>
      call.method === "PATCH" ? json({ ...CAPACITOR, ...(call.body as object) }) : undefined,
    );
    renderPages(<RepairsPage key="r" />);
    await screen.findByText("Cambio de capacitor");

    await userEvent.click(screen.getByRole("button", { name: "Renombrar Cambio de capacitor" }));
    const input = screen.getByLabelText("Nombre nuevo");
    await userEvent.clear(input);
    await userEvent.type(input, "Cambio de capacitor de marcha");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await userEvent.click(
      await screen.findByRole("button", { name: "Desactivar Cambio de capacitor" }),
    );

    await waitFor(() => {
      const patches = calls.filter((call) => call.method === "PATCH");
      expect(patches.map((call) => call.body)).toEqual([
        { name: "Cambio de capacitor de marcha" },
        { is_active: false },
      ]);
      expect(patches[0].path).toBe("/api/admin/repairs/r3");
    });
  });

  it("al desactivar una falla vuelve a pedir las reparaciones", async () => {
    const calls = stubApi((call) =>
      call.method === "PATCH" ? json({ ...ELECTRICA, is_active: false }) : undefined,
    );
    renderPages(<FailuresPage key="f" />, <RepairsPage key="r" />);
    await screen.findByText("Cambio de capacitor");
    const repairsBefore = calls.filter((call) => call.path === "/api/admin/repairs").length;

    await userEvent.click(
      screen.getByRole("button", { name: "Desactivar Falla eléctrica o mecánica" }),
    );

    await waitFor(() =>
      expect(calls.filter((call) => call.path === "/api/admin/repairs").length).toBeGreaterThan(
        repairsBefore,
      ),
    );
  });
});
