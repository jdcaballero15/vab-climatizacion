import { useState, type FormEvent } from "react";

import type { Crew } from "../crews/types";
import { useCrews } from "../crews/useCrews";
import { businessToday, formatDay, nextDay } from "./labels";
import type { Assignment, OrderListItem } from "./types";
import { useAssignOrder, useReassignOrder } from "./useOrders";

/**
 * Asignar una Pendiente (E04-03), reprogramar una que volvió de la escuadrilla o
 * reasignar una Asignada o En curso (E04-04).
 */
export type AssignMode = "assign" | "reprogram" | "reassign";

interface AssignOrderFormProps {
  order: OrderListItem;
  mode: AssignMode;
  onAssigned: (assignment: Assignment, crew: Crew) => void;
  onCancel: () => void;
}

const TITLES: Record<AssignMode, string> = {
  assign: "Asignar",
  reprogram: "Reprogramar",
  reassign: "Reasignar",
};

function missingFields(crewId: string, scheduledFor: string): string | null {
  const missing = [!crewId && "la escuadrilla", !scheduledFor && "la fecha prevista"].filter(
    (item): item is string => Boolean(item),
  );
  if (missing.length === 0) {
    return null;
  }
  const last = missing.pop();
  return `Falta ${missing.length ? `${missing.join(", ")} y ${last}` : last}.`;
}

/** Al reprogramar, la misma escuadrilla y mañana; al reasignar, lo vigente. Se pueden cambiar. */
function initialValues(order: OrderListItem, mode: AssignMode): [string, string] {
  if (mode === "reprogram" && order.returned) {
    return [order.returned.crew_id, nextDay(businessToday())];
  }
  return ["", ""];
}

/** Escuadrilla responsable y día previsto (sin hora). La API rechaza también lo inválido. */
export function AssignOrderForm({ order, mode, onAssigned, onCancel }: AssignOrderFormProps) {
  const crews = useCrews(false);
  const assignOrder = useAssignOrder(order.id);
  const reassignOrder = useReassignOrder(order.id);
  const mutation = mode === "reassign" ? reassignOrder : assignOrder;
  const [initialCrew, initialDate] = initialValues(order, mode);
  const [crewId, setCrewId] = useState(initialCrew);
  const [scheduledFor, setScheduledFor] = useState(initialDate);
  const [reason, setReason] = useState("");
  const [missing, setMissing] = useState<string | null>(null);
  // La API ya las trae activas y ordenadas (E02-09).
  const options = crews.data ?? [];
  const label = `${TITLES[mode]} la orden N° ${order.number}`;
  const id = (field: string) => `assign-${order.id}-${field}`;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const problem = missingFields(crewId, scheduledFor);
    setMissing(problem);
    const crew = options.find((item) => item.id === crewId);
    if (problem || !crew) {
      return;
    }
    const text = reason.trim();
    mutation.mutate(
      { crew_id: crewId, scheduled_for: scheduledFor, ...(text ? { reason: text } : {}) },
      { onSuccess: (assignment) => onAssigned(assignment, crew) },
    );
  }

  return (
    <form className="clients__form" onSubmit={handleSubmit} aria-label={label}>
      {mode === "reassign" && order.status === "in_progress" && (
        <p className="clients__warning" role="alert">
          {order.assignment
            ? `${order.assignment.crew_name} la está trabajando. `
            : "La escuadrilla la está trabajando. "}
          Si la reasignás, desaparece de su celular y la nueva escuadrilla la tiene que iniciar.
        </p>
      )}
      {mode === "reassign" && order.assignment && (
        <p>
          Ahora: {order.assignment.crew_name}, {formatDay(order.assignment.scheduled_for)}.
        </p>
      )}
      <label htmlFor={id("crew")}>Escuadrilla</label>
      <select id={id("crew")} value={crewId} onChange={(event) => setCrewId(event.target.value)}>
        <option value="">Elegí una escuadrilla</option>
        {options.map((crew) => (
          <option key={crew.id} value={crew.id}>
            {/* Se puede asignar igual: el celular se asocia en Escuadrillas y técnicos. */}
            {crew.app_user ? crew.name : `${crew.name} (sin celular)`}
          </option>
        ))}
      </select>
      {crews.isError && <p role="alert">No se pudieron cargar las escuadrillas.</p>}
      <label htmlFor={id("date")}>Fecha prevista</label>
      <input
        id={id("date")}
        type="date"
        min={businessToday()}
        value={scheduledFor}
        onChange={(event) => setScheduledFor(event.target.value)}
      />
      {mode !== "assign" && (
        <>
          <label htmlFor={id("reason")}>Motivo (opcional)</label>
          <input
            id={id("reason")}
            maxLength={255}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
        </>
      )}
      {missing && (
        <p className="clients__error" role="alert">
          {missing}
        </p>
      )}
      {mutation.isError && (
        <p className="clients__error" role="alert">
          {mutation.error.message}
        </p>
      )}
      <button type="submit" disabled={mutation.isPending}>
        {mode === "reassign" ? "Confirmar reasignación" : "Confirmar asignación"}
      </button>
      <button type="button" onClick={onCancel}>
        {mode === "assign" ? "Cancelar" : "Volver"}
      </button>
    </form>
  );
}
