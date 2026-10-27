import type { components } from "../../api/schema";
import { isOverdue, relativeDay } from "./dates";

type Order = components["schemas"]["OrderTechnicianOut"];

const STATUS_LABELS: Partial<Record<Order["status"], string>> = {
  assigned: "Asignada",
  in_progress: "En curso",
};

export function statusLabel(status: Order["status"]): string {
  return STATUS_LABELS[status] ?? status;
}

/** Fecha prevista relativa a hoy ("Hoy", "Mañana"...), con "Vencida" si ya pasó. */
export function dueLabel(scheduledFor: string, today: string): { text: string; overdue: boolean } {
  const overdue = isOverdue(scheduledFor, today);
  const day = relativeDay(scheduledFor, today);
  return { text: overdue ? `Vencida · ${day}` : day, overdue };
}

type NotDoneReason = components["schemas"]["NotDoneReason"];
type EquipmentCondition = components["schemas"]["EquipmentCondition"];

/** Motivos de "No se pudo hacer", como en el prototipo del cliente (E05-08). */
export const NOT_DONE_REASONS: [NotDoneReason, string][] = [
  ["client_absent", "Cliente ausente o sin acceso"],
  ["missing_part", "Falta repuesto o herramienta"],
  ["beyond_repair", "El equipo no tiene arreglo"],
];

export const EQUIPMENT_CONDITIONS: [EquipmentCondition, string][] = [
  ["working", "Funcionando bien"],
  ["working_with_notes", "Funciona con observaciones"],
  ["not_working", "No funciona"],
];
