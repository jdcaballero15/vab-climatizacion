import { useState, type FormEvent } from "react";

import type { Crew } from "../crews/types";
import { useCrews } from "../crews/useCrews";
import { businessToday } from "./labels";
import type { Assignment, OrderListItem } from "./types";
import { useAssignOrder } from "./useOrders";

interface AssignOrderFormProps {
  order: OrderListItem;
  onAssigned: (assignment: Assignment, crew: Crew) => void;
  onCancel: () => void;
}

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

/** Escuadrilla responsable y día previsto (sin hora). La API rechaza también lo inválido. */
export function AssignOrderForm({ order, onAssigned, onCancel }: AssignOrderFormProps) {
  const crews = useCrews(false);
  const assignOrder = useAssignOrder(order.id);
  const [crewId, setCrewId] = useState("");
  const [scheduledFor, setScheduledFor] = useState("");
  const [missing, setMissing] = useState<string | null>(null);
  // La API ya las trae activas y ordenadas (E02-09).
  const options = crews.data ?? [];
  const label = `Asignar la orden N° ${order.number}`;
  const id = (field: string) => `assign-${order.id}-${field}`;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const problem = missingFields(crewId, scheduledFor);
    setMissing(problem);
    const crew = options.find((item) => item.id === crewId);
    if (problem || !crew) {
      return;
    }
    assignOrder.mutate(
      { crew_id: crewId, scheduled_for: scheduledFor },
      { onSuccess: (assignment) => onAssigned(assignment, crew) },
    );
  }

  return (
    <form className="clients__form" onSubmit={handleSubmit} aria-label={label}>
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
      {missing && (
        <p className="clients__error" role="alert">
          {missing}
        </p>
      )}
      {assignOrder.isError && (
        <p className="clients__error" role="alert">
          {assignOrder.error.message}
        </p>
      )}
      <button type="submit" disabled={assignOrder.isPending}>
        Confirmar asignación
      </button>
      <button type="button" onClick={onCancel}>
        Cancelar
      </button>
    </form>
  );
}
