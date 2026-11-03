export function everyText(months: number): string {
  return months === 1 ? "Todos los meses" : `Cada ${months} meses`;
}

// Las del prototipo del cliente (2, 3, 4 y 6) más mensual y anual.
export const EVERY_OPTIONS = [1, 2, 3, 4, 6, 12];

export const SKIP_REASONS: Record<string, string> = {
  equipment_deleted: "el equipo o el cliente está dado de baja",
  work_type_inactive: "el tipo de trabajo está desactivado",
};
