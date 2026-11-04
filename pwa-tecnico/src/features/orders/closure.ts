import type { components } from "../../api/schema";
import { parseQuantity, type MaterialDraft } from "./materials";

export type ClosureOptions = components["schemas"]["ClosureOptionsTechnicianOut"];
export type ClosureCreate = components["schemas"]["ClosureCreate"];
export type ClosureOutcome = ClosureCreate["outcome"];
export type EquipmentCondition = components["schemas"]["EquipmentCondition"];
export type NotDoneReason = components["schemas"]["NotDoneReason"];
export type NoSignatureReason = components["schemas"]["NoSignatureReason"];
export type WorkshopStage = components["schemas"]["WorkshopStage"];
export type CheckResult = components["schemas"]["CheckResult"];

/** Respuesta a un paso del checklist de mantenimiento (E07-06 y E07-08). */
export interface CheckDraft {
  result: CheckResult;
  /** Lo que encontraron: obligatoria en No OK. */
  observation: string;
  /** Solo en No OK: el cierre pasa a pedir falla y reparación (E07-08). */
  requiresRepair: boolean;
}

/** Retiro o devolución de taller (E06): el cliente entrega o recibe el equipo y firma. */
export function isHandover(options: ClosureOptions): boolean {
  return options.workshop_stage === "pickup" || options.workshop_stage === "delivery";
}

/** El trabajo en el galpón (E06-05): no se firma. */
export function isBench(options: ClosureOptions): boolean {
  return options.workshop_stage === "workshop";
}

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
  /** Materiales usados (E05-05). Sin precios: la escuadrilla nunca los ve. */
  materials: MaterialDraft[];
  /** Checklist de mantenimiento (E07-06), por id del paso. Sin clave: sin responder. */
  checklist: Record<string, CheckDraft>;
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
  materials: [],
  checklist: {},
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
  | "checklist"
  | "parts"
  | "photo_ids"
  | "observation"
  | "signature"
  | "signer_name"
  | "no_signature_text";

export type ClosureErrors = Partial<Record<ClosureField, string>>;

/**
 * El checklist de una orden de mantenimiento (E07-06). Con "No se pudo hacer" no va; con
 * otra visita o retiro se puede mandar, completo, para no perder lo revisado.
 */
export function asksChecklist(draft: ClosureDraft, options: ClosureOptions): boolean {
  return options.checklist.length > 0 && draft.outcome !== "not_done";
}

/** Algún paso No OK pide reparación (E07-08). */
export function repairNeeded(draft: ClosureDraft, options: ClosureOptions): boolean {
  return (
    asksChecklist(draft, options) &&
    options.checklist.some((item) => draft.checklist[item.id]?.requiresRepair === true)
  );
}

/**
 * Falla y reparación obligatorias con Resuelta: si el tipo de trabajo las pide o, en
 * mantenimiento, si un paso requiere reparación (E07-08).
 */
export function failureRepairRequired(draft: ClosureDraft, options: ClosureOptions): boolean {
  // Retiro y devolución no las piden: eso se carga en el galpón (E06).
  return (
    (options.requires_failure_repair || repairNeeded(draft, options)) &&
    draft.outcome === "done" &&
    !isHandover(options)
  );
}

/** Pasos que faltan marcar, o No OK sin observación (E07-06, criterio 2), por id. */
export function checklistProblems(
  draft: ClosureDraft,
  options: ClosureOptions,
): Record<string, string> {
  if (!asksChecklist(draft, options)) {
    return {};
  }
  const answered = options.checklist.some((item) => draft.checklist[item.id]);
  const problems: Record<string, string> = {};
  for (const item of options.checklist) {
    const check = draft.checklist[item.id];
    if (!check) {
      // Terminada pide todos; otra visita o retiro, todos o ninguno.
      if (draft.outcome === "done" || answered) {
        problems[item.id] = "Marcá OK o No OK.";
      }
    } else if (check.result === "not_ok" && !check.observation.trim()) {
      problems[item.id] = "Escribí qué encontraste.";
    }
  }
  return problems;
}

/**
 * Con "No se pudo hacer" no se pregunta cómo quedó el equipo (E05-04, criterio 7), ni en
 * el retiro o la devolución de taller (E06).
 */
export function asksEquipmentCondition(draft: ClosureDraft, options: ClosureOptions): boolean {
  return draft.outcome !== "not_done" && !isHandover(options);
}

export function observationRequired(draft: ClosureDraft, options: ClosureOptions): boolean {
  return (
    draft.failure === OTHER ||
    draft.repair === OTHER ||
    (asksEquipmentCondition(draft, options) && draft.equipmentCondition === "working_with_notes") ||
    draft.outcome === "needs_revisit"
  );
}

/** El retiro o la devolución hechos se firman sí o sí: no se ofrece "no firma" (E06). */
export function signatureMandatory(draft: ClosureDraft, options: ClosureOptions): boolean {
  return isHandover(options) && draft.outcome === "done";
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
  const parts = ids(options.parts);
  const restored: ClosureDraft = {
    ...saved,
    technicianIds: saved.technicianIds.filter((id) => technicians.has(id)),
    taskIds: saved.taskIds.filter((id) => tasks.has(id)),
    // Un borrador guardado antes de E05-05 no tiene materiales.
    materials: (saved.materials ?? []).filter(
      (line) => line.part === OTHER || parts.has(line.part),
    ),
    // Ni checklist, si es anterior a E07-06.
    checklist: Object.fromEntries(
      options.checklist.flatMap((item) => {
        const check = saved.checklist?.[item.id];
        return check ? [[item.id, check]] : [];
      }),
    ),
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
  if (
    draft.outcome !== null &&
    asksEquipmentCondition(draft, options) &&
    !draft.equipmentCondition
  ) {
    errors.equipment_condition = "Elegí cómo quedó el equipo.";
  }
  const checks = Object.values(checklistProblems(draft, options));
  if (checks.length > 0) {
    errors.checklist = checks.includes("Marcá OK o No OK.")
      ? "Marcá OK o No OK en todos los pasos."
      : "Escribí qué encontraste en cada paso No OK.";
  }
  const materialError = materialsError(draft, options);
  if (materialError) {
    errors.parts = materialError;
  }
  if (observationRequired(draft, options) && !draft.observation.trim()) {
    errors.observation =
      draft.outcome === "needs_revisit" ? "Escribí qué falta." : "Escribí una observación.";
  }
  // E05-07, criterios 2 y 3: la firma con su nombre, o el motivo por el que no hay. En el
  // galpón no se firma; en el retiro o la devolución hechos, la firma es obligatoria (E06).
  if (isBench(options)) {
    return errors;
  }
  if (draft.noSignatureReason === null || signatureMandatory(draft, options)) {
    if (!signed) {
      errors.signature = signatureMandatory(draft, options)
        ? "Pedile la firma al cliente: entrega o recibe el equipo."
        : "Pedile la firma al cliente o elegí por qué no firma.";
    } else if (!draft.signerName.trim()) {
      errors.signer_name = "Escribí el nombre de quien firma.";
    }
  } else if (draft.noSignatureReason === "other" && !draft.noSignatureText.trim()) {
    errors.no_signature_text = "Escribí por qué no firma.";
  }
  return errors;
}

function materialsError(draft: ClosureDraft, options: ClosureOptions): string | null {
  for (const line of draft.materials) {
    if (line.part === OTHER && !line.otherText.trim()) {
      return "Escribí qué material es.";
    }
    if (parseQuantity(line.quantity) === null) {
      const name =
        line.part === OTHER
          ? line.otherText.trim()
          : (options.parts.find((part) => part.id === line.part)?.name ?? "un material");
      return `Revisá la cantidad de ${name}.`;
    }
  }
  return null;
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
    parts: draft.materials.map((line) => ({
      part_id: line.part === OTHER ? null : line.part,
      other_text: line.part === OTHER ? line.otherText.trim() : null,
      quantity: parseQuantity(line.quantity) ?? line.quantity,
    })),
    checklist: outcome === "not_done" ? [] : checklistPart(draft),
  };
}

function checklistPart(draft: ClosureDraft): ClosureCreate["checklist"] {
  return Object.entries(draft.checklist).map(([itemId, check]) =>
    check.result === "ok"
      ? { check_item_id: itemId, result: "ok", observation: null, requires_repair: false }
      : {
          check_item_id: itemId,
          result: "not_ok",
          observation: check.observation.trim() || null,
          requires_repair: check.requiresRepair,
        },
  );
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
