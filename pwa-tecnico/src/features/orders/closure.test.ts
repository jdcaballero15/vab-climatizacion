import { describe, expect, it } from "vitest";

import {
  EMPTY_DRAFT,
  OTHER,
  missingFields,
  repairsFor,
  restoreDraft,
  toClosurePayload,
  type ClosureDraft,
  type ClosureOptions,
} from "./closure";

const OPTIONS: ClosureOptions = {
  technicians: [{ id: "t1", name: "Ana Ficticia" }],
  tasks: [{ id: "k1", name: "Limpiar filtros" }],
  requires_failure_repair: true,
  failures: [
    { id: "f1", name: "No enfría", repairs: [{ id: "r1", name: "Carga de gas" }] },
    { id: "f2", name: "Pierde agua", repairs: [] },
  ],
};

function draft(overrides: Partial<ClosureDraft> = {}): ClosureDraft {
  return {
    ...EMPTY_DRAFT,
    technicianIds: ["t1"],
    outcome: "done",
    failure: "f1",
    repair: "r1",
    equipmentCondition: "working",
    noSignatureReason: "refused",
    ...overrides,
  };
}

describe("missingFields", () => {
  it("un cierre completo no tiene faltantes", () => {
    expect(missingFields(draft(), OPTIONS)).toEqual({});
  });

  // E05-04, criterios 2 y 8; E05-08, criterio 1.
  it("pide quiénes fueron y el resultado", () => {
    expect(missingFields(EMPTY_DRAFT, OPTIONS)).toEqual({
      technician_ids: "Tildá quiénes fueron.",
      outcome: "Elegí el resultado.",
      signature: "Pedile la firma al cliente o elegí por qué no firma.",
    });
  });

  // E05-07, criterio 2: la firma o el motivo, con cualquier resultado.
  it("pide la firma o el motivo por el que no hay", () => {
    expect(missingFields(draft({ noSignatureReason: null }), OPTIONS)).toEqual({
      signature: "Pedile la firma al cliente o elegí por qué no firma.",
    });
    expect(missingFields(draft({ noSignatureReason: "client_absent" }), OPTIONS)).toEqual({});
    expect(
      missingFields(draft({ noSignatureReason: "other", noSignatureText: " " }), OPTIONS),
    ).toEqual({ no_signature_text: "Escribí por qué no firma." });
  });

  // E05-07, criterio 3.
  it("con la firma trazada pide el nombre de quien firma", () => {
    const signed = draft({ noSignatureReason: null, signerName: " " });
    expect(missingFields(signed, OPTIONS, true)).toEqual({
      signer_name: "Escribí el nombre de quien firma.",
    });
    expect(missingFields({ ...signed, signerName: "Rosa Ficticia" }, OPTIONS, true)).toEqual({});
  });

  // E05-04, criterio 4.
  it("con Resuelta y un tipo que la pide, exige falla y reparación", () => {
    expect(missingFields(draft({ failure: "", repair: "" }), OPTIONS)).toEqual({
      failure_id: "Elegí la falla.",
      repair_id: "Elegí la reparación.",
    });
  });

  it("no exige falla ni reparación si el tipo no las pide o no está resuelta", () => {
    const sinFalla = { failure: "", repair: "" };
    expect(missingFields(draft(sinFalla), { ...OPTIONS, requires_failure_repair: false })).toEqual(
      {},
    );
    expect(
      missingFields(draft({ ...sinFalla, outcome: "needs_revisit", observation: "x" }), OPTIONS),
    ).toEqual({});
  });

  // E05-04, criterio 6.
  it('con "Otro" pide cuál y la observación', () => {
    expect(missingFields(draft({ failure: OTHER, repair: OTHER }), OPTIONS)).toEqual({
      failure_other_text: "Escribí cuál es la falla.",
      repair_other_text: "Escribí cuál es la reparación.",
      observation: "Escribí una observación.",
    });
  });

  // E05-04, criterio 7.
  it("pide cómo quedó el equipo y, con observaciones, la observación", () => {
    expect(missingFields(draft({ equipmentCondition: null }), OPTIONS)).toEqual({
      equipment_condition: "Elegí cómo quedó el equipo.",
    });
    expect(missingFields(draft({ equipmentCondition: "working_with_notes" }), OPTIONS)).toEqual({
      observation: "Escribí una observación.",
    });
  });

  // E05-08, criterios 3 y 4.
  it("otra visita pide qué falta; no se pudo hacer no pide el equipo", () => {
    expect(missingFields(draft({ outcome: "needs_revisit", observation: " " }), OPTIONS)).toEqual({
      observation: "Escribí qué falta.",
    });
    expect(
      missingFields(
        draft({
          outcome: "not_done",
          notDoneReason: "client_absent",
          failure: "",
          repair: "",
          equipmentCondition: null,
        }),
        OPTIONS,
      ),
    ).toEqual({});
  });
});

describe("repairsFor", () => {
  it("solo las reparaciones de la falla elegida", () => {
    expect(repairsFor(draft(), OPTIONS)).toEqual([{ id: "r1", name: "Carga de gas" }]);
    expect(repairsFor(draft({ failure: "f2" }), OPTIONS)).toEqual([]);
    expect(repairsFor(draft({ failure: OTHER }), OPTIONS)).toEqual([]);
  });
});

describe("toClosurePayload", () => {
  it("arma el cierre resuelto con ids de las listas", () => {
    expect(toClosurePayload(draft({ taskIds: ["k1"], observation: "  " }), "key")).toEqual({
      idempotency_key: "key",
      outcome: "done",
      technician_ids: ["t1"],
      task_ids: ["k1"],
      failure_id: "f1",
      failure_other_text: null,
      repair_id: "r1",
      repair_other_text: null,
      equipment_condition: "working",
      not_done_reason: null,
      observation: null,
      photo_ids: [],
      signature: null,
      no_signature_reason: "refused",
      no_signature_text: null,
    });
  });

  // E05-07, criterio 1.
  it("manda la firma subida con el nombre de quien firma", () => {
    const signed = draft({ noSignatureReason: null, signerName: " Rosa Ficticia " });
    expect(toClosurePayload(signed, "key", [], "s1")).toMatchObject({
      signature: { file_id: "s1", signer_name: "Rosa Ficticia" },
      no_signature_reason: null,
      no_signature_text: null,
    });
  });

  it("con un motivo elegido manda el motivo aunque haya firma, y el texto solo con Otro", () => {
    expect(
      toClosurePayload(
        draft({ noSignatureReason: "other", noSignatureText: " Lluvia " }),
        "key",
        [],
        "s1",
      ),
    ).toMatchObject({ signature: null, no_signature_reason: "other", no_signature_text: "Lluvia" });
    expect(
      toClosurePayload(draft({ noSignatureReason: "client_absent", noSignatureText: "x" }), "key"),
    ).toMatchObject({ no_signature_reason: "client_absent", no_signature_text: null });
  });

  // E05-06, criterio 3: las fotos van como ids, en el orden del formulario.
  it("suma los ids de las fotos subidas", () => {
    expect(toClosurePayload(draft(), "key", ["p2", "p1"]).photo_ids).toEqual(["p2", "p1"]);
  });

  it('manda el texto de "Otro" en lugar del id', () => {
    const payload = toClosurePayload(
      draft({ failure: OTHER, failureOther: " Ruido ", repair: OTHER, repairOther: "Ajuste" }),
      "key",
    );
    expect(payload).toMatchObject({
      failure_id: null,
      failure_other_text: "Ruido",
      repair_id: null,
      repair_other_text: "Ajuste",
    });
  });

  it("con No se pudo hacer manda el motivo y no el estado del equipo", () => {
    const payload = toClosurePayload(
      draft({ outcome: "not_done", notDoneReason: "missing_part" }),
      "key",
    );
    expect(payload).toMatchObject({
      outcome: "not_done",
      not_done_reason: "missing_part",
      equipment_condition: null,
    });
  });
});

// E05-13: un borrador guardado puede tener opciones que la oficina sacó después.
describe("restoreDraft", () => {
  it("deja igual un borrador con opciones vigentes", () => {
    const saved = draft({ taskIds: ["k1"], observation: "Filtro sucio" });
    expect(restoreDraft(saved, OPTIONS)).toEqual(saved);
  });

  it("saca técnicos y tareas que ya no están en las listas", () => {
    const saved = draft({ technicianIds: ["t1", "t9"], taskIds: ["k1", "k9"] });
    expect(restoreDraft(saved, OPTIONS)).toMatchObject({ technicianIds: ["t1"], taskIds: ["k1"] });
  });

  it("una falla que ya no está vuelve a sin elegir, con su reparación", () => {
    const saved = draft({ failure: "f9", repair: "r1" });
    expect(restoreDraft(saved, OPTIONS)).toMatchObject({ failure: "", repair: "" });
  });

  it("una reparación que ya no es de la falla vuelve a sin elegir", () => {
    expect(restoreDraft(draft({ repair: "r9" }), OPTIONS)).toMatchObject({
      failure: "f1",
      repair: "",
    });
  });

  it('mantiene "Otro" con su texto', () => {
    const saved = draft({
      failure: OTHER,
      failureOther: "Ruido",
      repair: OTHER,
      repairOther: "Ajuste",
    });
    expect(restoreDraft(saved, OPTIONS)).toEqual(saved);
  });
});
