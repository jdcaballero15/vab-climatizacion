import type { OrderChannel } from "./types";

export const CHANNEL_LABELS: Record<OrderChannel, string> = {
  whatsapp: "WhatsApp",
  email: "Mail",
  phone: "Teléfono",
  in_person: "Presencial",
};

// Hora de la empresa, para que la fecha no cambie según el huso de la PC.
const DATE_FORMAT = new Intl.DateTimeFormat("es-AR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  timeZone: "America/Argentina/Buenos_Aires",
});

/** Fecha sin hora, dd/mm/aaaa. */
export function formatDate(isoDate: string): string {
  return DATE_FORMAT.format(new Date(isoDate));
}
