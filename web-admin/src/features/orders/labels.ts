import type { OrderChannel } from "./types";

export const CHANNEL_LABELS: Record<OrderChannel, string> = {
  whatsapp: "WhatsApp",
  email: "Mail",
  phone: "Teléfono",
  in_person: "Presencial",
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
