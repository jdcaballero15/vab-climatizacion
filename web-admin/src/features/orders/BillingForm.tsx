import { useState, type FormEvent } from "react";

import { BILLING_STATUS_LABELS, formatDateTime, formatMoney } from "./labels";
import type { BillingStatus, OrderListItem } from "./types";
import { useSaveBilling } from "./useOrders";

// Pesos con hasta dos decimales; se acepta coma o punto para los centavos.
const AMOUNT = /^\d{1,10}([.,]\d{1,2})?$/;

function toAmount(text: string): string | null {
  const clean = text.trim();
  return AMOUNT.test(clean) ? clean.replace(",", ".") : null;
}

/**
 * Importes de repuestos y mano de obra y estado de cobro de una terminada (E04-14,
 * versión mínima). Sin nada cargado, la orden está pendiente de enviar a cobrar.
 */
export function BillingForm({ order }: { order: OrderListItem }) {
  const saved = order.billing ?? null;
  const save = useSaveBilling(order.id);
  const [parts, setParts] = useState(saved ? String(Number(saved.parts_amount)) : "");
  const [labor, setLabor] = useState(saved ? String(Number(saved.labor_amount)) : "");
  const [status, setStatus] = useState<BillingStatus>(saved?.status ?? "pending");
  const [invoice, setInvoice] = useState(saved?.invoice_number ?? "");
  const [invalid, setInvalid] = useState(false);
  const [done, setDone] = useState(false);
  const id = (field: string) => `billing-${order.id}-${field}`;

  const partsAmount = toAmount(parts || "0");
  const laborAmount = toAmount(labor || "0");
  const total =
    partsAmount !== null && laborAmount !== null ? Number(partsAmount) + Number(laborAmount) : null;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setDone(false);
    if (partsAmount === null || laborAmount === null) {
      setInvalid(true);
      return;
    }
    setInvalid(false);
    save.mutate(
      {
        parts_amount: partsAmount,
        labor_amount: laborAmount,
        status,
        invoice_number: status === "invoiced" ? invoice : null,
      },
      { onSuccess: () => setDone(true) },
    );
  }

  return (
    <form
      className="clients__form orders__billing"
      onSubmit={handleSubmit}
      aria-label={`Importes y cobro de la orden N° ${order.number}`}
    >
      <h4>Importes y cobro</h4>
      <div className="orders__billing-amounts">
        <div>
          <label htmlFor={id("parts")}>Repuestos ($)</label>
          <input
            id={id("parts")}
            inputMode="decimal"
            value={parts}
            onChange={(event) => setParts(event.target.value)}
            placeholder="0"
          />
        </div>
        <div>
          <label htmlFor={id("labor")}>Mano de obra ($)</label>
          <input
            id={id("labor")}
            inputMode="decimal"
            value={labor}
            onChange={(event) => setLabor(event.target.value)}
            placeholder="0"
          />
        </div>
      </div>
      <p className="orders__billing-total">
        Total: <strong>{total === null ? "-" : formatMoney(total)}</strong>
      </p>

      <label htmlFor={id("status")}>Estado de cobro</label>
      <select
        id={id("status")}
        value={status}
        onChange={(event) => setStatus(event.target.value as BillingStatus)}
      >
        {(Object.keys(BILLING_STATUS_LABELS) as BillingStatus[]).map((value) => (
          <option key={value} value={value}>
            {BILLING_STATUS_LABELS[value]}
          </option>
        ))}
      </select>
      {status === "invoiced" && (
        <>
          <label htmlFor={id("invoice")}>N° de factura (opcional)</label>
          <input
            id={id("invoice")}
            value={invoice}
            onChange={(event) => setInvoice(event.target.value)}
            maxLength={50}
          />
        </>
      )}

      {invalid && (
        <p className="clients__error" role="alert">
          Revisá los importes: solo números, con hasta dos decimales.
        </p>
      )}
      {save.isError && (
        <p className="clients__error" role="alert">
          {save.error.message}
        </p>
      )}
      {done && <p role="status">Importes guardados.</p>}
      {saved && !done && (
        <p className="muted">
          Última carga: {saved.updated_by_name}, {formatDateTime(saved.updated_at)}
        </p>
      )}
      <button type="submit" disabled={save.isPending}>
        {save.isPending ? "Guardando…" : "Guardar importes"}
      </button>
    </form>
  );
}
