import type {
  BillingStatus,
  Cancellation,
  CancelReason,
  ClosureDetail,
  OrderChannel,
  OrderListItem,
  OrderView,
  WorkshopStage,
  ReturnedFromCrew,
  TimelineEntry,
} from "./types";

export const CHANNEL_LABELS: Record<OrderChannel, string> = {
  whatsapp: "WhatsApp",
  email: "Mail",
  phone: "Teléfono",
  in_person: "Presencial",
};

/** El estado de una orden, en singular (tarjetas, detalle e historial del cliente). */
export const ORDER_STATUS_LABELS: Record<OrderListItem["status"], string> = {
  pending: "Pendiente",
  assigned: "Asignada",
  in_progress: "En curso",
  done: "Terminada",
  invoiced: "Facturada",
  paid: "Cobrada",
  cancelled: "Cancelada",
};

/** Plural, como se elige en el listado de Órdenes. */
export const LIST_STATUS_LABELS: Record<OrderView, string> = {
  pending: "Pendientes",
  assigned: "Asignadas",
  in_progress: "En curso",
  done: "Terminadas",
  cancelled: "Canceladas",
  in_workshop: "En el galpón",
};

/** Etapas de una orden de taller (E06), en el orden en que se hacen. */
export const WORKSHOP_STAGE_LABELS: Record<WorkshopStage, string> = {
  pickup: "Retiro",
  workshop: "Galpón",
  delivery: "Devolución",
};

/** "Taller · Retiro": la etapa que toca, o la última si ya está terminada. */
export function workshopStageText(stage: WorkshopStage): string {
  return `Taller · ${WORKSHOP_STAGE_LABELS[stage]}`;
}

// Lista a validar con la oficina (E04-07).
export const CANCEL_REASON_LABELS: Record<CancelReason, string> = {
  entered_by_mistake: "Cargada por error",
  duplicate: "Duplicada",
  client_cancelled: "El cliente la canceló",
  other: "Otro",
};

export const OUTCOME_LABELS: Record<ReturnedFromCrew["outcome"], string> = {
  done: "Resuelta",
  needs_revisit: "Requiere otra visita",
  not_done: "No se pudo hacer",
  needs_pickup: "Requiere retiro",
};

export const NOT_DONE_REASON_LABELS: Record<
  NonNullable<ReturnedFromCrew["not_done_reason"]>,
  string
> = {
  client_absent: "Cliente ausente o sin acceso",
  missing_part: "Falta repuesto o herramienta",
  beyond_repair: "El equipo no tiene arreglo",
};

// Las mismas palabras que la app del celular (E05-04).
export const EQUIPMENT_CONDITION_LABELS: Record<
  NonNullable<ClosureDetail["equipment_condition"]>,
  string
> = {
  working: "Funcionando bien",
  working_with_notes: "Funciona con observaciones",
  not_working: "No funciona",
};

// Hora de la empresa, para que la fecha no cambie según el huso de la PC.
const BUSINESS_TZ = "America/Argentina/Buenos_Aires";
const DATE_FORMAT = new Intl.DateTimeFormat("es-AR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  timeZone: BUSINESS_TZ,
});

/** Fecha sin hora, dd/mm/aaaa. */
export function formatDate(isoDate: string): string {
  return DATE_FORMAT.format(new Date(isoDate));
}

const TIME_FORMAT = new Intl.DateTimeFormat("es-AR", {
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
  timeZone: BUSINESS_TZ,
});

/** Fecha con hora, "dd/mm/aaaa hh:mm" en la hora de la empresa. */
export function formatDateTime(isoDate: string): string {
  const date = new Date(isoDate);
  return `${DATE_FORMAT.format(date)} ${TIME_FORMAT.format(date)}`;
}

/** Un día sin hora ("2026-10-26") como dd/mm/aaaa, sin pasar por Date (evita el corrimiento UTC). */
export function formatDay(isoDay: string): string {
  const [year, month, day] = isoDay.split("-");
  return `${day}/${month}/${year}`;
}

/** Hoy en Argentina como aaaa-mm-dd, el formato de un <input type="date">. */
export function businessToday(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: BUSINESS_TZ }).format(new Date());
}

/** El día siguiente a uno dado (aaaa-mm-dd), sin depender del huso de la PC. */
export function nextDay(isoDay: string): string {
  const day = new Date(`${isoDay}T12:00:00Z`);
  day.setUTCDate(day.getUTCDate() + 1);
  return day.toISOString().slice(0, 10);
}

/** Por qué volvió de la escuadrilla, en una línea (E05-08, criterio 5). */
export function returnedText(returned: ReturnedFromCrew): string {
  const detail = [
    returned.not_done_reason && NOT_DONE_REASON_LABELS[returned.not_done_reason],
    returned.observation,
  ]
    .filter(Boolean)
    .join(". ");
  const outcome = OUTCOME_LABELS[returned.outcome];
  return (
    `Volvió de ${returned.crew_name} el ${formatDate(returned.closed_at)}: ` +
    (detail ? `${outcome}. ${detail}` : outcome)
  );
}

/** Motivo de una cancelación; con "Otro", el texto que se escribió. */
export function cancelReasonText(cancellation: Cancellation): string {
  return cancellation.reason === "other" && cancellation.reason_text
    ? cancellation.reason_text
    : CANCEL_REASON_LABELS[cancellation.reason];
}

/** Iniciales para un avatar. */
export function initials(name: string): string {
  const words = name.split(" ").filter(Boolean);
  // "Escuadrilla 1" se lee mejor como "E1" que como "E" sola.
  return words
    .slice(0, 2)
    .map((word) => (/^\d+$/.test(word) ? word : word[0]?.toUpperCase()))
    .join("");
}

type NoSignatureReason = NonNullable<ClosureDetail["no_signature_reason"]>;

/** Por qué el cierre no tiene firma del cliente (E05-07, D-011). */
export const NO_SIGNATURE_REASON_LABELS: Record<NoSignatureReason, string> = {
  client_absent: "Cliente ausente",
  refused: "No quiso firmar",
  other: "Otro",
};

/** Estado de cobro de una terminada (E04-14); sin importes cargados está pendiente. */
export const BILLING_STATUS_LABELS: Record<BillingStatus, string> = {
  pending: "Pendiente de enviar a cobrar",
  invoiced: "Facturada",
};

const MONEY = new Intl.NumberFormat("es-AR", { style: "currency", currency: "ARS" });

/** Importe en pesos como lo manda la API ("15000.50"). */
export function formatMoney(amount: string | number): string {
  return MONEY.format(Number(amount));
}

// Pesos con hasta dos decimales; se acepta coma o punto para los centavos.
const AMOUNT = /^\d{1,10}([.,]\d{1,2})?$/;

/** Importe escrito a mano ("1800,5") como lo espera la API ("1800.5"), o null si no vale. */
export function toAmount(text: string): string | null {
  const clean = text.trim();
  return AMOUNT.test(clean) ? clean.replace(",", ".") : null;
}

// Cantidad de un material: mayor que cero, coma o punto, hasta tres decimales (E05-05).
// Misma regla que el celular (pwa-tecnico/src/features/orders/materials.ts).
const QUANTITY = /^\d{1,9}([.,]\d{1,3})?$/;

/** Cantidad escrita ("2,25") como la espera la API ("2.25"), o null si no vale. */
export function toQuantity(text: string): string | null {
  const clean = text.trim();
  // "1.500" puede ser mil quinientos o uno y medio: se pide con coma o sin punto.
  if (!QUANTITY.test(clean) || /\.\d{3}$/.test(clean)) {
    return null;
  }
  const value = clean.replace(",", ".");
  return Number(value) > 0 ? value : null;
}

// Sin separador de miles: "1.500" se leería como 1,5 al volver a guardarla.
const QUANTITY_FORMAT = new Intl.NumberFormat("es-AR", {
  maximumFractionDigits: 3,
  useGrouping: false,
});

/** Cantidad como la manda la API ("1.500") para mostrarla ("1,5"). */
export function formatQuantity(quantity: string): string {
  return QUANTITY_FORMAT.format(Number(quantity));
}

const EVENT_LABELS: Record<string, string> = {
  created: "Creada",
  assigned: "Asignada",
  unassigned: "Desasignada",
  reassigned: "Reasignada",
  review_approved: "Aprobada",
  review_returned: "Devuelta a la escuadrilla",
  converted_to_workshop: "Pasó a taller",
  equipment_changed: "Cambio de equipo",
  materials_changed: "Cambio de materiales",
  billing_invoiced: "Marcada como facturada",
};

/** Cómo se lee un paso de la línea de tiempo de la orden (E04-06). */
export function timelineLabel(entry: TimelineEntry): string {
  if (entry.event_type === "status_change") {
    if (entry.to_status === "in_progress") {
      return "Iniciada por la escuadrilla";
    }
    if (entry.to_status === "done") {
      return "Cerrada por la escuadrilla";
    }
    if (entry.to_status === "pending") {
      return "Volvió de la escuadrilla";
    }
    if (entry.to_status) {
      return ORDER_STATUS_LABELS[entry.to_status];
    }
  }
  return EVENT_LABELS[entry.event_type] ?? entry.event_type;
}
