// Días sin hora ("2026-10-26"). "Hoy" lo manda el backend (día de Argentina), así no
// depende del reloj ni del huso del celular.

const MS_PER_DAY = 86_400_000;

// Date.UTC solo para contar días entre dos fechas: no hay huso que corra el día.
function dayNumber(isoDay: string): number {
  const [year, month, day] = isoDay.split("-").map(Number);
  return Date.UTC(year, month - 1, day) / MS_PER_DAY;
}

/** dd/mm/aaaa, sin pasar por Date. */
export function formatDay(isoDay: string): string {
  const [year, month, day] = isoDay.split("-");
  return `${day}/${month}/${year}`;
}

/** "Hoy", "Mañana", "Ayer" o la fecha. */
export function relativeDay(isoDay: string, today: string): string {
  const diff = dayNumber(isoDay) - dayNumber(today);
  if (diff === 0) return "Hoy";
  if (diff === 1) return "Mañana";
  if (diff === -1) return "Ayer";
  return formatDay(isoDay);
}

export function isOverdue(isoDay: string, today: string): boolean {
  return isoDay < today;
}

// La hora de un cierre se muestra en la de la empresa, como en la oficina.
const BUSINESS_TZ = "America/Argentina/Buenos_Aires";
// en-CA da "aaaa-mm-dd", el mismo formato que los días de la API.
const DAY_FORMAT = new Intl.DateTimeFormat("en-CA", { timeZone: BUSINESS_TZ });
const TIME_FORMAT = new Intl.DateTimeFormat("es-AR", {
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
  timeZone: BUSINESS_TZ,
});

/** Día y hora de un instante: "Hoy 14:30", "Ayer 09:10" o "26/10/2026 18:00" (E05-14). */
export function relativeMoment(
  isoDateTime: string,
  today: string = DAY_FORMAT.format(new Date()),
): string {
  const date = new Date(isoDateTime);
  return `${relativeDay(DAY_FORMAT.format(date), today)} ${TIME_FORMAT.format(date)}`;
}
