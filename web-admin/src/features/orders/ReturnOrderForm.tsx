import { useState, type FormEvent } from "react";

import { businessToday } from "./labels";
import type { Assignment, OrderListItem } from "./types";
import { useReturnOrder } from "./useOrders";

interface ReturnOrderFormProps {
  order: OrderListItem;
  onReturned: (assignment: Assignment) => void;
  onClose: () => void;
}

/**
 * Devuelve una Terminada a la escuadrilla que la cerró, con motivo obligatorio (E04-08,
 * criterio 3). La escuadrilla ve el motivo en el celular. Una aprobada no se devuelve:
 * lo rechaza la API con su mensaje.
 */
export function ReturnOrderForm({ order, onReturned, onClose }: ReturnOrderFormProps) {
  const returnOrder = useReturnOrder(order.id);
  const [reason, setReason] = useState("");
  const [scheduledFor, setScheduledFor] = useState(businessToday());
  const [missing, setMissing] = useState<string | null>(null);
  const crewName = order.completed?.crew_name ?? "la escuadrilla que la cerró";
  const id = (field: string) => `return-${order.id}-${field}`;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = reason.trim();
    const problem = !text ? "Falta el motivo." : !scheduledFor ? "Falta la fecha prevista." : null;
    setMissing(problem);
    if (problem) {
      return;
    }
    returnOrder.mutate({ reason: text, scheduled_for: scheduledFor }, { onSuccess: onReturned });
  }

  return (
    <form
      className="clients__form"
      onSubmit={handleSubmit}
      aria-label={`Devolver la orden N° ${order.number} a la escuadrilla`}
    >
      <p>
        Vuelve a Asignadas a {crewName}, que la ve en el celular con el motivo y la tiene que volver
        a cerrar.
      </p>
      <label htmlFor={id("reason")}>Motivo</label>
      <textarea
        id={id("reason")}
        maxLength={500}
        rows={2}
        value={reason}
        onChange={(event) => setReason(event.target.value)}
      />
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
      {returnOrder.isError && (
        <p className="clients__error" role="alert">
          {returnOrder.error.message}
        </p>
      )}
      <button type="submit" disabled={returnOrder.isPending}>
        Confirmar devolución
      </button>
      <button type="button" onClick={onClose}>
        Volver
      </button>
    </form>
  );
}
