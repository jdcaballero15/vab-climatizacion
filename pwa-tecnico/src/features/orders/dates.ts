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
