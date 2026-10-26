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
