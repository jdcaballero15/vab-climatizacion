import type {
  Cancellation,
  CancelReason,
  ListableStatus,
  OrderChannel,
  ReturnedFromCrew,
} from "./types";

export const CHANNEL_LABELS: Record<OrderChannel, string> = {
  whatsapp: "WhatsApp",
  email: "Mail",
  phone: "Teléfono",
  in_person: "Presencial",
};

/** Plural, como se elige en el listado de Órdenes. */
export const LIST_STATUS_LABELS: Record<ListableStatus, string> = {
  pending: "Pendientes",
  assigned: "Asignadas",
  in_progress: "En curso",
  cancelled: "Canceladas",
};

// Lista a validar con la oficina (E04-07).
export const CANCEL_REASON_LABELS: Record<CancelReason, string> = {
  entered_by_mistake: "Cargada por error",
  duplicate: "Duplicada",
  client_cancelled: "El cliente la canceló",
  other: "Otro",
};

const OUTCOME_LABELS: Record<ReturnedFromCrew["outcome"], string> = {
  done: "Resuelta",
  needs_revisit: "Requiere otra visita",
  not_done: "No se pudo hacer",
  needs_pickup: "Requiere retiro",
};

const NOT_DONE_REASON_LABELS: Record<NonNullable<ReturnedFromCrew["not_done_reason"]>, string> = {
  client_absent: "Cliente ausente o sin acceso",
  missing_part: "Falta repuesto o herramienta",
  beyond_repair: "El equipo no tiene arreglo",
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

/** Un día sin hora ("2026-10-26") como dd/mm/aaaa, sin pasar por Date (evita el corrimiento UTC). */
export function formatDay(isoDay: string): string {
  const [year, month, day] = isoDay.split("-");
  return `${day}/${month}/${year}`;
}

/** Hoy en Argentina como aaaa-mm-dd, el formato de un <input type="date">. */
export function businessToday(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: BUSINESS_TZ }).format(new Date());
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
