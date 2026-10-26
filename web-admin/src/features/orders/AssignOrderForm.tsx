import { useState, type FormEvent } from "react";

import type { UserAdmin } from "../users/types";
import { useUsers } from "../users/useUsers";
import { businessToday } from "./labels";
import type { Assignment, PendingOrder } from "./types";
import { useAssignOrder } from "./useOrders";

interface AssignOrderFormProps {
  order: PendingOrder;
  onAssigned: (assignment: Assignment, technician: UserAdmin) => void;
  onCancel: () => void;
}

function missingFields(technicianId: string, scheduledFor: string): string | null {
  const missing = [!technicianId && "el técnico", !scheduledFor && "la fecha prevista"].filter(
    (item): item is string => Boolean(item),
  );
  if (missing.length === 0) {
    return null;
  }
  const last = missing.pop();
  return `Falta ${missing.length ? `${missing.join(", ")} y ${last}` : last}.`;
}

/** Técnico responsable y día previsto (sin hora). La API rechaza también lo inválido. */
export function AssignOrderForm({ order, onAssigned, onCancel }: AssignOrderFormProps) {
  const users = useUsers();
  const assignOrder = useAssignOrder(order.id);
  const [technicianId, setTechnicianId] = useState("");
  const [scheduledFor, setScheduledFor] = useState("");
  const [missing, setMissing] = useState<string | null>(null);
  const technicians = (users.data ?? [])
    .filter((user) => user.role === "technician" && user.is_active)
    .sort((a, b) => a.full_name.localeCompare(b.full_name, "es"));
  const label = `Asignar la orden N° ${order.number}`;
  const id = (field: string) => `assign-${order.id}-${field}`;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const problem = missingFields(technicianId, scheduledFor);
    setMissing(problem);
    const technician = technicians.find((user) => user.id === technicianId);
    if (problem || !technician) {
      return;
    }
    assignOrder.mutate(
      { technician_id: technicianId, scheduled_for: scheduledFor },
      { onSuccess: (assignment) => onAssigned(assignment, technician) },
    );
  }

  return (
    <form className="clients__form" onSubmit={handleSubmit} aria-label={label}>
      <label htmlFor={id("technician")}>Técnico</label>
      <select
        id={id("technician")}
        value={technicianId}
        onChange={(event) => setTechnicianId(event.target.value)}
      >
        <option value="">Elegí un técnico</option>
        {technicians.map((user) => (
          <option key={user.id} value={user.id}>
            {user.full_name}
          </option>
        ))}
      </select>
      {users.isError && <p role="alert">No se pudieron cargar los técnicos.</p>}
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
