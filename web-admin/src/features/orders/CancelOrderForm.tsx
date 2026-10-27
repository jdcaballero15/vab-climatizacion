import { useState, type FormEvent } from "react";

import { CANCEL_REASON_LABELS } from "./labels";
import type { Cancellation, CancelReason, OrderListItem } from "./types";
import { useCancelOrder } from "./useOrders";

interface CancelOrderFormProps {
  order: OrderListItem;
  onCancelled: (cancellation: Cancellation) => void;
  onClose: () => void;
}

/** Motivo de la cancelación (E04-07). La API rechaza también lo inválido. */
export function CancelOrderForm({ order, onCancelled, onClose }: CancelOrderFormProps) {
  const cancelOrder = useCancelOrder(order.id);
  const [reason, setReason] = useState<CancelReason | "">("");
  const [reasonText, setReasonText] = useState("");
  const [missing, setMissing] = useState<string | null>(null);
  const label = `Cancelar la orden N° ${order.number}`;
  const id = (field: string) => `cancel-${order.id}-${field}`;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = reasonText.trim();
    const problem = !reason
      ? "Falta el motivo."
      : reason === "other" && !text
        ? "Falta escribir el motivo."
        : null;
    setMissing(problem);
    if (problem || !reason) {
      return;
    }
    cancelOrder.mutate(
      { reason, reason_text: reason === "other" ? text : null },
      { onSuccess: onCancelled },
    );
  }

  return (
    <form className="clients__form" onSubmit={handleSubmit} aria-label={label}>
      {order.status === "in_progress" && (
        <p className="clients__warning" role="alert">
          {order.assignment
            ? `${order.assignment.crew_name} la está trabajando. `
            : "La escuadrilla la está trabajando. "}
          Si la cancelás, desaparece de su celular y no la va a poder cerrar.
        </p>
      )}
      <label htmlFor={id("reason")}>Motivo</label>
      <select
        id={id("reason")}
        value={reason}
        onChange={(event) => setReason(event.target.value as CancelReason | "")}
      >
        <option value="">Elegí el motivo</option>
        {Object.entries(CANCEL_REASON_LABELS).map(([value, text]) => (
          <option key={value} value={value}>
            {text}
          </option>
        ))}
      </select>
      {reason === "other" && (
        <>
          <label htmlFor={id("text")}>Cuál es el motivo</label>
          <input
            id={id("text")}
            maxLength={255}
            value={reasonText}
            onChange={(event) => setReasonText(event.target.value)}
          />
        </>
      )}
      {missing && (
        <p className="clients__error" role="alert">
          {missing}
        </p>
      )}
      {cancelOrder.isError && (
        <p className="clients__error" role="alert">
          {cancelOrder.error.message}
        </p>
      )}
      <button type="submit" disabled={cancelOrder.isPending}>
        Confirmar cancelación
      </button>
      <button type="button" onClick={onClose}>
        Volver
      </button>
    </form>
  );
}
