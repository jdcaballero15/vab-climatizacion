import type { components } from "../../api/schema";

export type ClosureOptions = components["schemas"]["ClosureOptionsTechnicianOut"];
export type ClosureCreate = components["schemas"]["ClosureCreate"];
export type ClosureOutcome = ClosureCreate["outcome"];
export type EquipmentCondition = components["schemas"]["EquipmentCondition"];
export type NotDoneReason = components["schemas"]["NotDoneReason"];
export type NoSignatureReason = components["schemas"]["NoSignatureReason"];

/** Valor de los selectores de falla y reparación para "Otro" (no es del catálogo). */
export const OTHER = "__other__";

/** Lo que la escuadrilla va cargando en el formulario de cierre (E05-04, E05-08). */
export interface ClosureDraft {
  technicianIds: string[];
  taskIds: string[];
  outcome: ClosureOutcome | null;
  notDoneReason: NotDoneReason | null;
  /** "" sin elegir, OTHER o el id de la falla. */
  failure: string;
  failureOther: string;
  /** "" sin elegir, OTHER o el id de la reparación. */
  repair: string;
  repairOther: string;
  equipmentCondition: EquipmentCondition | null;
  observation: string;
  /** Aclaración de quien firma (E05-07). El trazo viaja aparte, como las fotos. */
  signerName: string;
  /** Por qué no hay firma. Con un motivo elegido, el trazo no se manda. */
  noSignatureReason: NoSignatureReason | null;
  noSignatureText: string;
}

export const EMPTY_DRAFT: ClosureDraft = {
  technicianIds: [],
  taskIds: [],
  outcome: null,
  notDoneReason: null,
  failure: "",
  failureOther: "",
  repair: "",
  repairOther: "",
  equipmentCondition: null,
  observation: "",
  signerName: "",
  noSignatureReason: null,
  noSignatureText: "",
};

/** Campos que se marcan en el formulario. Los de la API coinciden con su `field` (422). */
export type ClosureField =
  | "technician_ids"
  | "task_ids"
  | "outcome"
  | "not_done_reason"
  | "failure_id"
  | "failure_other_text"
  | "repair_id"
  | "repair_other_text"
  | "equipment_condition"
  | "photo_ids"
  | "observation"
  | "signature"
  | "signer_name"
  | "no_signature_text";

export type ClosureErrors = Partial<Record<ClosureField, string>>;

/** Falla y reparación obligatorias: el tipo de trabajo las pide y el resultado es Resuelta. */
export function failureRepairRequired(draft: ClosureDraft, options: ClosureOptions): boolean {
  return options.requires_failure_repair && draft.outcome === "done";
}

/** Con "No se pudo hacer" no se pregunta cómo quedó el equipo (E05-04, criterio 7). */
export function asksEquipmentCondition(draft: ClosureDraft): boolean {
  return draft.outcome !== "not_done";
}

export function observationRequired(draft: ClosureDraft): boolean {
  return (
    draft.failure === OTHER ||
    draft.repair === OTHER ||
    (asksEquipmentCondition(draft) && draft.equipmentCondition === "working_with_notes") ||
    draft.outcome === "needs_revisit"
  );
}

/** Reparaciones de la falla elegida. Con "Otro" o sin falla, ninguna de la lista. */
export function repairsFor(draft: ClosureDraft, options: ClosureOptions) {
  return options.failures.find((failure) => failure.id === draft.failure)?.repairs ?? [];
}

/**
 * Un borrador guardado en el celular (E05-13) contra las listas de hoy: lo que la oficina
 * sacó desde entonces vuelve a sin elegir, en lugar de mandarse y volver con un 422.
 */
export function restoreDraft(saved: ClosureDraft, options: ClosureOptions): ClosureDraft {
  const ids = (items: { id: string }[]) => new Set(items.map((item) => item.id));
  const technicians = ids(options.technicians);
  const tasks = ids(options.tasks);
  const keeps = (value: string, items: { id: string }[]) =>
    value === "" || value === OTHER || ids(items).has(value);
  const restored: ClosureDraft = {
    ...saved,
    technicianIds: saved.technicianIds.filter((id) => technicians.has(id)),
    taskIds: saved.taskIds.filter((id) => tasks.has(id)),
  };
  if (!keeps(restored.failure, options.failures)) {
    return { ...restored, failure: "", failureOther: "", repair: "", repairOther: "" };
  }
  if (!keeps(restored.repair, repairsFor(restored, options))) {
    return { ...restored, repair: "", repairOther: "" };
  }
  return restored;
}

/**
 * Lo que falta para cerrar, con las mismas reglas que la API (services/closures.py).
 * `signed`: hay un trazo de firma en el lienzo.
 */
export function missingFields(
  draft: ClosureDraft,
  options: ClosureOptions,
  signed = false,
): ClosureErrors {
  const errors: ClosureErrors = {};
  if (draft.technicianIds.length === 0) {
    errors.technician_ids = "Tildá quiénes fueron.";
  }
  if (draft.outcome === null) {
    errors.outcome = "Elegí el resultado.";
  }
  const required = failureRepairRequired(draft, options);
  if (draft.failure === OTHER && !draft.failureOther.trim()) {
    errors.failure_other_text = "Escribí cuál es la falla.";
  } else if (required && draft.failure === "") {
    errors.failure_id = "Elegí la falla.";
  }
  if (draft.repair === OTHER && !draft.repairOther.trim()) {
    errors.repair_other_text = "Escribí cuál es la reparación.";
  } else if (required && draft.repair === "") {
    errors.repair_id = "Elegí la reparación.";
  }
  if (draft.outcome !== null && asksEquipmentCondition(draft) && !draft.equipmentCondition) {
    errors.equipment_condition = "Elegí cómo quedó el equipo.";
  }
  if (observationRequired(draft) && !draft.observation.trim()) {
    errors.observation =
      draft.outcome === "needs_revisit" ? "Escribí qué falta." : "Escribí una observación.";
  }
  // E05-07, criterios 2 y 3: la firma con su nombre, o el motivo por el que no hay.
  if (draft.noSignatureReason === null) {
    if (!signed) {
      errors.signature = "Pedile la firma al cliente o elegí por qué no firma.";
    } else if (!draft.signerName.trim()) {
      errors.signer_name = "Escribí el nombre de quien firma.";
    }
  } else if (draft.noSignatureReason === "other" && !draft.noSignatureText.trim()) {
    errors.no_signature_text = "Escribí por qué no firma.";
  }
  return errors;
}

/**
 * Arma el pedido de cierre. Solo se llama con un borrador sin faltantes y las fotos y la
 * firma subidas. Con un motivo elegido va el motivo, aunque haya un trazo en el lienzo.
 */
export function toClosurePayload(
  draft: ClosureDraft,
  idempotencyKey: string,
  photoIds: string[] = [],
  signatureFileId: string | null = null,
): ClosureCreate {
  const outcome = draft.outcome ?? "done";
  const pick = (value: string) => (value === "" || value === OTHER ? null : value);
  const text = (value: string) => value.trim() || null;
  return {
    idempotency_key: idempotencyKey,
    outcome,
    technician_ids: draft.technicianIds,
    task_ids: draft.taskIds,
    failure_id: pick(draft.failure),
    failure_other_text: draft.failure === OTHER ? text(draft.failureOther) : null,
    repair_id: pick(draft.repair),
    repair_other_text: draft.repair === OTHER ? text(draft.repairOther) : null,
    equipment_condition: outcome === "not_done" ? null : draft.equipmentCondition,
    not_done_reason: outcome === "not_done" ? draft.notDoneReason : null,
    observation: text(draft.observation),
    photo_ids: photoIds,
    ...signaturePart(draft, signatureFileId),
  };
}

function signaturePart(
  draft: ClosureDraft,
  fileId: string | null,
): Pick<ClosureCreate, "signature" | "no_signature_reason" | "no_signature_text"> {
  const reason = draft.noSignatureReason;
  if (reason !== null || fileId === null) {
    return {
      signature: null,
      no_signature_reason: reason,
      no_signature_text: reason === "other" ? draft.noSignatureText.trim() || null : null,
    };
  }
  return {
    signature: { file_id: fileId, signer_name: draft.signerName.trim() || null },
    no_signature_reason: null,
    no_signature_text: null,
  };
}
