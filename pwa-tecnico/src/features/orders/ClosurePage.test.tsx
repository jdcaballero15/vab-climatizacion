import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { components } from "../../api/schema";
import { ClosurePage } from "./ClosurePage";

type Options = components["schemas"]["ClosureOptionsTechnicianOut"];
type ClosureCreate = components["schemas"]["ClosureCreate"];

const ORDER_ID = "6f1c2a9e-0000-4000-8000-000000000001";
const ANA = "a0000000-0000-4000-8000-000000000001";
const LUIS = "a0000000-0000-4000-8000-000000000002";
const TASK = "b0000000-0000-4000-8000-000000000001";
const FAILURE = "c0000000-0000-4000-8000-000000000001";
const REPAIR = "d0000000-0000-4000-8000-000000000001";

function options(overrides: Partial<Options> = {}): Options {
  return {
    technicians: [
      { id: ANA, name: "Ana Ficticia" },
      { id: LUIS, name: "Luis Ficticio" },
    ],
    tasks: [{ id: TASK, name: "Limpiar filtros" }],
    requires_failure_repair: true,
    failures: [
      { id: FAILURE, name: "No enfría", repairs: [{ id: REPAIR, name: "Carga de gas" }] },
      { id: "c0000000-0000-4000-8000-000000000002", name: "Pierde agua", repairs: [] },
    ],
    ...overrides,
  };
}

const DETAIL = {
  id: ORDER_ID,
  number: 3,
  status: "in_progress",
  work_type_name: "Reparación",
  description: null,
  client_name: "Sanatorio Ficticio",
  scheduled_for: "2026-10-27",
  today: "2026-10-27",
  requester_area: null,
  site: { address: "Calle 1", reference: null, map_url: "https://maps", contact_names: [] },
  equipment: null,
  tasks: ["Limpiar filtros"],
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const CLOSED = {
  id: "e0000000-0000-4000-8000-000000000001",
  outcome: "done",
  order_status: "done",
  closed_at: "2026-10-27T12:00:00Z",
};

/** Simula la API: detalle, listas y el cierre. Devuelve los cierres enviados. */
function stubApi(
  closure: () => Response | Promise<Response> = () => json(CLOSED, 201),
  closureOptions: () => Response = () => json(options()),
) {
  const sent: ClosureCreate[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (request: Request) => {
      const path = new URL(request.url).pathname;
      if (request.method === "POST") {
        sent.push((await request.json()) as ClosureCreate);
        return closure();
      }
      if (path.endsWith("/closure-options")) {
        return closureOptions();
      }
      if (path.endsWith("/tech/orders")) {
        return json({ crew: null, today: "2026-10-27", orders: [] });
      }
      return json(DETAIL);
    }),
  );
  return sent;
}

function OrdersList() {
  const state = useLocation().state as { notice?: string } | null;
  return <h1>Lista: {state?.notice}</h1>;
}

function renderClosure() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[`/ordenes/${ORDER_ID}/cerrar`]}>
        <Routes>
          <Route path="/" element={<OrdersList />} />
          <Route path="/ordenes/:orderId" element={<h1>Detalle de la orden</h1>} />
          <Route path="/ordenes/:orderId/cerrar" element={<ClosurePage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const user = userEvent.setup();
const click = (name: string | RegExp) => user.click(screen.getByRole("button", { name }));

async function fillResolved() {
  await click("Ana Ficticia");
  await click("Limpiar filtros");
  await click("Resuelta");
  await user.selectOptions(screen.getByRole("combobox", { name: /Falla/ }), "No enfría");
  await user.selectOptions(screen.getByRole("combobox", { name: /Reparación/ }), "Carga de gas");
  await click("Funcionando bien");
}

afterEach(() => vi.restoreAllMocks());

describe("ClosurePage", () => {
  // E05-04, criterios 2, 3 y 5: las listas del cierre.
  it("muestra técnicos, tareas, resultados y las listas de falla y reparación", async () => {
    stubApi();
    renderClosure();

    expect(await screen.findByRole("button", { name: "Ana Ficticia" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Cerrar orden N° 3" })).toBeInTheDocument();
    expect(screen.getByText("Reparación · Sanatorio Ficticio")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Luis Ficticio" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Limpiar filtros" })).toBeInTheDocument();
    // E05-08, criterio 1: dos grupos, con los motivos de "No se pudo hacer".
    expect(screen.getByText("Se hizo")).toBeInTheDocument();
    expect(screen.getByText("No se pudo hacer")).toBeInTheDocument();
    for (const name of [
      "Resuelta",
      "Requiere otra visita",
      "Cliente ausente o sin acceso",
      "Falta repuesto o herramienta",
      "El equipo no tiene arreglo",
    ]) {
      expect(screen.getByRole("button", { name })).toBeInTheDocument();
    }
    const failure = screen.getByRole("combobox", { name: /Falla/ });
    expect(
      within(failure)
        .getAllByRole("option")
        .map((o) => o.textContent),
    ).toEqual(["Elegí la falla", "No enfría", "Pierde agua", "Otro"]);
    expect(screen.getByRole("combobox", { name: /Reparación/ })).toBeDisabled();
  });

  it("la reparación lista solo las de la falla elegida", async () => {
    stubApi();
    renderClosure();

    const failure = await screen.findByRole("combobox", { name: /Falla/ });
    const repair = screen.getByRole("combobox", { name: /Reparación/ });
    await user.selectOptions(failure, "No enfría");
    expect(
      within(repair)
        .getAllByRole("option")
        .map((o) => o.textContent),
    ).toEqual(["Elegí la reparación", "Carga de gas", "Otro"]);
    await user.selectOptions(repair, "Carga de gas");

    // Cambiar la falla borra la reparación elegida.
    await user.selectOptions(failure, "Pierde agua");
    expect(repair).toHaveValue("");
    expect(
      within(repair)
        .getAllByRole("option")
        .map((o) => o.textContent),
    ).toEqual(["Elegí la reparación", "Otro"]);
  });

  // E05-04, criterio 8: se marca qué falta y no se envía.
  it("marca lo que falta y no envía", async () => {
    const sent = stubApi();
    renderClosure();

    await user.click(await screen.findByRole("button", { name: "Finalizar orden" }));

    const missing = screen.getByRole("alert");
    expect(missing).toHaveTextContent("Tildá quiénes fueron.");
    expect(missing).toHaveTextContent("Elegí el resultado.");
    expect(document.activeElement).toHaveAttribute("id", "closure-technicians");
    expect(sent).toEqual([]);

    // E05-04, criterio 4: con Resuelta, falla y reparación son obligatorias.
    await click("Ana Ficticia");
    await click("Resuelta");
    expect(screen.getByRole("alert")).toHaveTextContent("Elegí la falla.");
    expect(screen.getByRole("alert")).toHaveTextContent("Elegí la reparación.");
    expect(screen.getByRole("alert")).toHaveTextContent("Elegí cómo quedó el equipo.");
    expect(screen.getAllByText("(obligatoria)")).toHaveLength(2);
  });

  it("falla y reparación son opcionales si el tipo de trabajo no las pide", async () => {
    const sent = stubApi(undefined, () => json(options({ requires_failure_repair: false })));
    renderClosure();

    await user.click(await screen.findByRole("button", { name: "Ana Ficticia" }));
    await click("Resuelta");
    await click("Funcionando bien");
    await click("Finalizar orden");

    expect(await screen.findByRole("heading", { name: /Lista/ })).toBeInTheDocument();
    expect(sent[0]).toMatchObject({ outcome: "done", failure_id: null, repair_id: null });
  });

  // E05-04, criterios 2 a 4 y 7; E05-08, criterio 2.
  it("envía el cierre resuelto y vuelve a la lista con el aviso", async () => {
    const sent = stubApi();
    renderClosure();
    await screen.findByRole("button", { name: "Ana Ficticia" });

    await fillResolved();
    await click("Finalizar orden");

    expect(
      await screen.findByRole("heading", { name: "Lista: Orden N° 3 cerrada." }),
    ).toBeInTheDocument();
    expect(sent).toHaveLength(1);
    expect(sent[0]).toEqual({
      idempotency_key: expect.stringMatching(/^[0-9a-f-]{36}$/),
      outcome: "done",
      technician_ids: [ANA],
      task_ids: [TASK],
      failure_id: FAILURE,
      failure_other_text: null,
      repair_id: REPAIR,
      repair_other_text: null,
      equipment_condition: "working",
      not_done_reason: null,
      observation: null,
      photo_ids: [],
    });
  });

  // E05-04, criterio 6.
  it('con "Otro" pide cuál y la observación', async () => {
    const sent = stubApi();
    renderClosure();
    await user.click(await screen.findByRole("button", { name: "Ana Ficticia" }));
    await click("Resuelta");
    await user.selectOptions(screen.getByRole("combobox", { name: /Falla/ }), "Otro");
    await user.selectOptions(screen.getByRole("combobox", { name: /Reparación/ }), "Otro");
    await click("Funcionando bien");
    await click("Finalizar orden");

    const missing = screen.getByRole("alert");
    expect(missing).toHaveTextContent("Escribí cuál es la falla.");
    expect(missing).toHaveTextContent("Escribí cuál es la reparación.");
    expect(missing).toHaveTextContent("Escribí una observación.");

    await user.type(screen.getByRole("textbox", { name: "¿Cuál es la falla?" }), "Ruido");
    await user.type(screen.getByRole("textbox", { name: "¿Cuál es la reparación?" }), "Ajuste");
    await user.type(screen.getByRole("textbox", { name: /Observación/ }), "Ruido en el motor");
    await click("Finalizar orden");

    await screen.findByRole("heading", { name: /Lista/ });
    expect(sent[0]).toMatchObject({
      failure_id: null,
      failure_other_text: "Ruido",
      repair_id: null,
      repair_other_text: "Ajuste",
      observation: "Ruido en el motor",
    });
  });

  // E05-04, criterio 7: con observaciones, la observación es obligatoria.
  it("funciona con observaciones exige la observación", async () => {
    stubApi(undefined, () => json(options({ requires_failure_repair: false })));
    renderClosure();
    await user.click(await screen.findByRole("button", { name: "Ana Ficticia" }));
    await click("Resuelta");
    await click("Funciona con observaciones");
    await click("Finalizar orden");

    expect(screen.getByRole("alert")).toHaveTextContent("Escribí una observación.");
  });

  // E05-08, criterio 3.
  it("otra visita pide qué falta y devuelve la orden a la oficina", async () => {
    const sent = stubApi(() =>
      json({ ...CLOSED, outcome: "needs_revisit", order_status: "pending" }, 201),
    );
    renderClosure();
    await user.click(await screen.findByRole("button", { name: "Ana Ficticia" }));
    await click("Requiere otra visita");
    await click("Funcionando bien");
    await click("Finalizar orden");

    expect(screen.getByRole("alert")).toHaveTextContent("Escribí qué falta.");
    expect(screen.getByText("Contá qué falta para terminar el trabajo.")).toBeInTheDocument();

    await user.type(screen.getByRole("textbox", { name: /Observación/ }), "Falta el compresor");
    await click("Finalizar orden");

    expect(
      await screen.findByRole("heading", { name: "Lista: Orden N° 3 devuelta a la oficina." }),
    ).toBeInTheDocument();
    expect(sent[0]).toMatchObject({ outcome: "needs_revisit", observation: "Falta el compresor" });
  });

  // E05-08, criterio 4; E05-04, criterio 7: sin estado del equipo.
  it("no se pudo hacer manda el motivo y no pregunta por el equipo", async () => {
    const sent = stubApi(() =>
      json({ ...CLOSED, outcome: "not_done", order_status: "pending" }, 201),
    );
    renderClosure();
    await user.click(await screen.findByRole("button", { name: "Ana Ficticia" }));
    await click("Funcionando bien");
    await click("Cliente ausente o sin acceso");

    expect(screen.queryByRole("button", { name: "Funcionando bien" })).not.toBeInTheDocument();
    await click("Cerrar como no realizada");

    await screen.findByRole("heading", { name: /devuelta a la oficina/ });
    expect(sent[0]).toMatchObject({
      outcome: "not_done",
      not_done_reason: "client_absent",
      equipment_condition: null,
    });
  });

  // E05-04, criterio 8: el 422 de la API marca el campo.
  it("marca el campo que rechaza la API", async () => {
    stubApi(() =>
      json(
        {
          detail: {
            code: "technician_not_available",
            message: "Uno de los técnicos no está activo.",
            field: "technician_ids",
          },
        },
        422,
      ),
    );
    renderClosure();
    await screen.findByRole("button", { name: "Ana Ficticia" });
    await fillResolved();
    await click("Finalizar orden");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Uno de los técnicos no está activo.",
    );
    expect(document.getElementById("closure-technicians")).toHaveClass("closure__section--invalid");
  });

  // E05-12: reintentar después de un corte reusa la clave; no duplica el cierre.
  it("si se corta la conexión avisa y el reintento usa la misma clave", async () => {
    let calls = 0;
    const sent = stubApi(() => {
      calls += 1;
      if (calls === 1) {
        throw new TypeError("sin conexión");
      }
      return json(CLOSED, 200);
    });
    renderClosure();
    await screen.findByRole("button", { name: "Ana Ficticia" });
    await fillResolved();
    await click("Finalizar orden");

    expect(
      await screen.findByText(
        "No se pudo enviar el cierre. Revisá la conexión e intentá de nuevo.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ana Ficticia", pressed: true })).toBeInTheDocument();

    await click("Finalizar orden");
    await screen.findByRole("heading", { name: /Lista/ });
    expect(sent).toHaveLength(2);
    expect(sent[1].idempotency_key).toBe(sent[0].idempotency_key);
  });

  it("una clave usada en otra orden se cambia por una nueva", async () => {
    let calls = 0;
    const sent = stubApi(() => {
      calls += 1;
      if (calls === 1) {
        return json(
          {
            detail: {
              code: "idempotency_key_reused",
              message: "Este cierre ya se usó en otra orden. Volvé a abrir el cierre.",
              field: "idempotency_key",
            },
          },
          422,
        );
      }
      return json(CLOSED, 201);
    });
    renderClosure();
    await screen.findByRole("button", { name: "Ana Ficticia" });
    await fillResolved();
    await click("Finalizar orden");

    expect(await screen.findByRole("alert")).toHaveTextContent("Este cierre ya se usó");
    await click("Finalizar orden");
    await screen.findByRole("heading", { name: /Lista/ });
    expect(sent[1].idempotency_key).not.toBe(sent[0].idempotency_key);
  });

  // E05-04, criterio 10: una orden que no está En curso de la escuadrilla.
  it("avisa si la orden ya no está en curso para la escuadrilla", async () => {
    stubApi(undefined, () =>
      json({ detail: { code: "order_not_found", message: "No se encontró la orden." } }, 404),
    );
    renderClosure();

    expect(
      await screen.findByText("Esta orden ya no está en curso para tu escuadrilla."),
    ).toBeInTheDocument();
  });

  it("si al enviar la orden ya no está en curso, lo avisa", async () => {
    stubApi(() =>
      json({ detail: { code: "order_not_found", message: "No se encontró la orden." } }, 404),
    );
    renderClosure();
    await screen.findByRole("button", { name: "Ana Ficticia" });
    await fillResolved();
    await click("Finalizar orden");

    expect(
      await screen.findByText("Esta orden ya no está en curso para tu escuadrilla."),
    ).toBeInTheDocument();
  });

  it("vuelve al detalle de la orden", async () => {
    stubApi();
    renderClosure();

    await user.click(await screen.findByRole("link", { name: "Volver a la orden" }));
    expect(screen.getByRole("heading", { name: "Detalle de la orden" })).toBeInTheDocument();
  });
});
