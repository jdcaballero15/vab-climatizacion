import { useState, type FormEvent } from "react";

import { formatDateTime, formatDay, formatMoney, PAYMENT_METHOD_LABELS, toAmount } from "./labels";
import type { Billing, Charge, OrderListItem } from "./types";
import { useChangeCharge, useCharges, useOrderBilling, useSaveBilling } from "./useOrders";

/**
 * Importes de una orden cerrada (E04-14, E04-11): repuestos (total de materiales, E05-05),
 * mano de obra a mano y otros cargos con descripción e importe. Se editan con la orden
 * Terminada; facturada o cobrada, o para dirección, se ven sin editar.
 */
export function BillingForm({ order, readOnly }: { order: OrderListItem; readOnly?: boolean }) {
  const billing = useOrderBilling(order.id);
  const editable = !readOnly && order.status === "done";
  if (!billing.data) {
    return billing.isError ? (
      <p role="alert">No se pudieron cargar los importes.</p>
    ) : (
      <p className="muted">Cargando importes…</p>
    );
  }
  return (
    <section
      className="clients__form orders__billing"
      aria-label={`Importes y cobro de la orden N° ${order.number}`}
    >
      <h4>Importes y cobro</h4>
      {editable ? (
        <LaborForm order={order} billing={billing.data} />
      ) : (
        <p>
          Repuestos {formatMoney(billing.data.parts_amount)} · Mano de obra{" "}
          {formatMoney(billing.data.labor_amount)}
        </p>
      )}
      <ChargesEditor orderId={order.id} editable={editable} />
      <p className="orders__billing-total">
        Total: <strong>{formatMoney(billing.data.total)}</strong>
      </p>
      <InvoiceAndPayment billing={billing.data} />
    </section>
  );
}

function LaborForm({ order, billing }: { order: OrderListItem; billing: Billing }) {
  const save = useSaveBilling(order.id);
  const [labor, setLabor] = useState(
    Number(billing.labor_amount) ? String(Number(billing.labor_amount)) : "",
  );
  const [invalid, setInvalid] = useState(false);
  const [done, setDone] = useState(false);
  const id = `billing-${order.id}-labor`;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setDone(false);
    const amount = toAmount(labor || "0");
    if (amount === null) {
      setInvalid(true);
      return;
    }
    setInvalid(false);
    save.mutate({ labor_amount: amount }, { onSuccess: () => setDone(true) });
  }

  return (
    <form onSubmit={handleSubmit} aria-label={`Mano de obra de la orden N° ${order.number}`}>
      <div className="orders__billing-amounts">
        <div>
          <span className="orders__billing-label">Repuestos (materiales)</span>
          <p className="orders__billing-parts">{formatMoney(billing.parts_amount)}</p>
        </div>
        <div>
          <label htmlFor={id}>Mano de obra ($)</label>
          <input
            id={id}
            inputMode="decimal"
            value={labor}
            onChange={(event) => setLabor(event.target.value)}
            placeholder="0"
          />
        </div>
      </div>
      {invalid && (
        <p className="clients__error" role="alert">
          Revisá el importe: solo números, con hasta dos decimales.
        </p>
      )}
      {save.isError && (
        <p className="clients__error" role="alert">
          {save.error.message}
        </p>
      )}
      {done && <p role="status">Mano de obra guardada.</p>}
      {billing.updated_by_name && billing.updated_at && !done && (
        <p className="muted">
          Última carga: {billing.updated_by_name}, {formatDateTime(billing.updated_at)}
        </p>
      )}
      <button type="submit" disabled={save.isPending}>
        {save.isPending ? "Guardando…" : "Guardar mano de obra"}
      </button>
    </form>
  );
}

/** Otros cargos (visita, viáticos, lo que haga falta): cada cambio queda en la línea de
 * tiempo de la orden (E04-11, criterio 4). */
function ChargesEditor({ orderId, editable }: { orderId: string; editable: boolean }) {
  const charges = useCharges(orderId);
  const change = useChangeCharge(orderId);
  const [editing, setEditing] = useState<Charge | null>(null);
  const items = charges.data ?? [];

  return (
    <div className="orders__charges">
      <h5>Otros cargos</h5>
      {items.length === 0 && <p className="muted">Sin otros cargos.</p>}
      {items.length > 0 && (
        <ul>
          {items.map((charge) => (
            <li key={charge.id}>
              <span>{charge.description}</span> <strong>{formatMoney(charge.amount)}</strong>
              {editable && (
                <>
                  {" "}
                  <button
                    type="button"
                    className="btn--ghost btn--sm"
                    onClick={() => setEditing(charge)}
                    aria-label={`Corregir el cargo ${charge.description}`}
                  >
                    Corregir
                  </button>
                  <button
                    type="button"
                    className="btn--ghost btn--sm"
                    onClick={() => change.mutate({ kind: "remove", chargeId: charge.id })}
                    aria-label={`Sacar el cargo ${charge.description}`}
                  >
                    Sacar
                  </button>
                </>
              )}
            </li>
          ))}
        </ul>
      )}
      {editable && (
        <ChargeForm
          key={editing?.id ?? "new"}
          initial={editing}
          pending={change.isPending}
          error={change.isError ? change.error.message : null}
          onCancel={editing ? () => setEditing(null) : undefined}
          onSave={(body, onSaved) =>
            change.mutate(
              editing ? { kind: "update", chargeId: editing.id, body } : { kind: "add", body },
              {
                onSuccess: () => {
                  setEditing(null);
                  onSaved();
                },
              },
            )
          }
        />
      )}
    </div>
  );
}

function ChargeForm({
  initial,
  pending,
  error,
  onCancel,
  onSave,
}: {
  initial: Charge | null;
  pending: boolean;
  error: string | null;
  onCancel?: () => void;
  onSave: (body: { description: string; amount: string }, onSaved: () => void) => void;
}) {
  const [description, setDescription] = useState(initial?.description ?? "");
  const [amount, setAmount] = useState(initial ? String(Number(initial.amount)) : "");
  const [invalid, setInvalid] = useState<string | null>(null);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = toAmount(amount);
    if (!description.trim()) {
      setInvalid("Escribí qué es el cargo.");
      return;
    }
    if (value === null || amount.trim() === "") {
      setInvalid("Revisá el importe: solo números, con hasta dos decimales.");
      return;
    }
    setInvalid(null);
    onSave({ description: description.trim(), amount: value }, () => {
      setDescription("");
      setAmount("");
    });
  }

  return (
    <form
      className="orders__charge-form"
      onSubmit={handleSubmit}
      aria-label={initial ? "Corregir cargo" : "Agregar cargo"}
    >
      <label>
        Descripción
        <input
          value={description}
          maxLength={200}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="Por ejemplo, visita fuera de horario"
        />
      </label>
      <label>
        Importe ($)
        <input
          inputMode="decimal"
          value={amount}
          onChange={(event) => setAmount(event.target.value)}
        />
      </label>
      {(invalid ?? error) && (
        <p className="clients__error" role="alert">
          {invalid ?? error}
        </p>
      )}
      <button type="submit" disabled={pending}>
        {initial ? "Guardar cargo" : "Agregar cargo"}
      </button>
      {onCancel && (
        <button type="button" onClick={onCancel}>
          Cancelar
        </button>
      )}
    </form>
  );
}

function InvoiceAndPayment({ billing }: { billing: Billing }) {
  if (!billing.invoice) {
    return <p className="muted">Sin facturar.</p>;
  }
  const { invoice, payment } = billing;
  return (
    <p>
      Factura {invoice.number} del {formatDay(invoice.issued_on)}
      {invoice.order_numbers.length > 1 &&
        ` (cubre las órdenes ${invoice.order_numbers.map((n) => `N° ${n}`).join(", ")})`}
      {payment &&
        `. Cobrada el ${formatDay(payment.paid_on)} (${PAYMENT_METHOD_LABELS[payment.method]})`}
      .
    </p>
  );
}
