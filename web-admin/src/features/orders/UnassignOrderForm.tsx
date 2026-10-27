import { useState, type FormEvent } from "react";

import type { OrderListItem } from "./types";
import { useUnassignOrder } from "./useOrders";

interface UnassignOrderFormProps {
  order: OrderListItem;
  onUnassigned: () => void;
  onClose: () => void;
}

/** Devuelve una orden Asignada a Pendientes, con motivo opcional (E04-04, criterio 3). */
export function UnassignOrderForm({ order, onUnassigned, onClose }: UnassignOrderFormProps) {
  const unassignOrder = useUnassignOrder(order.id);
  const [reason, setReason] = useState("");
  const id = `unassign-${order.id}-reason`;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = reason.trim();
    unassignOrder.mutate(text ? { reason: text } : {}, { onSuccess: onUnassigned });
  }

  return (
    <form
      className="clients__form"
      onSubmit={handleSubmit}
      aria-label={`Desasignar la orden N° ${order.number}`}
    >
      <p>
        Vuelve a Pendientes sin escuadrilla ni fecha
        {order.assignment ? ` y desaparece del celular de ${order.assignment.crew_name}` : ""}.
      </p>
      <label htmlFor={id}>Motivo (opcional)</label>
      <input
        id={id}
        maxLength={255}
        value={reason}
        onChange={(event) => setReason(event.target.value)}
      />
      {unassignOrder.isError && (
        <p className="clients__error" role="alert">
          {unassignOrder.error.message}
        </p>
      )}
      <button type="submit" disabled={unassignOrder.isPending}>
        Confirmar desasignación
      </button>
      <button type="button" onClick={onClose}>
        Volver
      </button>
    </form>
  );
}
