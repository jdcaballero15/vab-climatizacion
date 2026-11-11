import { useState, type FormEvent } from "react";

import { businessToday, PAYMENT_METHOD_LABELS } from "./labels";
import type { Invoice, OrderListItem, PaymentMethod } from "./types";
import { useCreateInvoice, usePayment, useUpdateInvoice } from "./useOrders";

/**
 * Una factura para las terminadas elegidas (E04-09). Una misma factura puede cubrir varias
 * órdenes, por ejemplo las de un abonado; si alguna no se puede facturar (sin aprobar), la
 * API rechaza todas y dice cuál.
 */
export function NewInvoiceForm({
  orders,
  onDone,
  onCancel,
}: {
  orders: OrderListItem[];
  onDone: (invoice: Invoice) => void;
  onCancel: () => void;
}) {
  const create = useCreateInvoice();
  return (
    <InvoiceFields
      title={`Facturar ${orders.length === 1 ? "la orden" : `${orders.length} órdenes`}: ${orders
        .map((o) => `N° ${o.number}`)
        .join(", ")}`}
      submit="Registrar factura"
      pending={create.isPending}
      error={create.isError ? create.error.message : null}
      onCancel={onCancel}
      onSubmit={(number, issued_on) =>
        create.mutate(
          { number, issued_on, order_ids: orders.map((o) => o.id) },
          { onSuccess: onDone },
        )
      }
    />
  );
}

/** Corrige número o fecha; queda en la línea de tiempo de cada orden (criterio 4). */
export function EditInvoiceForm({
  invoice,
  onDone,
  onCancel,
}: {
  invoice: Invoice;
  onDone: () => void;
  onCancel: () => void;
}) {
  const update = useUpdateInvoice(invoice.id);
  return (
    <InvoiceFields
      title={`Corregir la factura ${invoice.number}`}
      submit="Guardar corrección"
      initialNumber={invoice.number}
      initialDate={invoice.issued_on}
      pending={update.isPending}
      error={update.isError ? update.error.message : null}
      onCancel={onCancel}
      onSubmit={(number, issued_on) => update.mutate({ number, issued_on }, { onSuccess: onDone })}
    />
  );
}

function InvoiceFields({
  title,
  submit,
  initialNumber = "",
  initialDate = businessToday(),
  pending,
  error,
  onCancel,
  onSubmit,
}: {
  title: string;
  submit: string;
  initialNumber?: string;
  initialDate?: string;
  pending: boolean;
  error: string | null;
  onCancel: () => void;
  onSubmit: (number: string, issuedOn: string) => void;
}) {
  const [number, setNumber] = useState(initialNumber);
  const [issuedOn, setIssuedOn] = useState(initialDate);
  const [missing, setMissing] = useState(false);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!number.trim() || !issuedOn) {
      setMissing(true);
      return;
    }
    setMissing(false);
    onSubmit(number.trim(), issuedOn);
  }

  return (
    <form className="clients__form orders__invoice" onSubmit={handleSubmit} aria-label={title}>
      <h4>{title}</h4>
      <label>
        N° de factura
        <input value={number} maxLength={50} onChange={(event) => setNumber(event.target.value)} />
      </label>
      <label>
        Fecha de la factura
        <input type="date" value={issuedOn} onChange={(event) => setIssuedOn(event.target.value)} />
      </label>
      {missing && (
        <p className="clients__error" role="alert">
          Completá el número y la fecha de la factura.
        </p>
      )}
      {error && (
        <p className="clients__error" role="alert">
          {error}
        </p>
      )}
      <button type="submit" className="btn--primary" disabled={pending}>
        {pending ? "Guardando…" : submit}
      </button>
      <button type="button" onClick={onCancel}>
        Cancelar
      </button>
    </form>
  );
}

/** Cobro de una facturada (E04-10): fecha y medio; el importe es el total de la orden. */
export function PaymentForm({
  order,
  onDone,
  onCancel,
}: {
  order: OrderListItem;
  onDone: () => void;
  onCancel: () => void;
}) {
  const payment = usePayment(order.id);
  const [paidOn, setPaidOn] = useState(businessToday());
  const [method, setMethod] = useState<PaymentMethod | "">("");
  const [missing, setMissing] = useState(false);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!paidOn || !method) {
      setMissing(true);
      return;
    }
    setMissing(false);
    payment.mutate({ kind: "register", body: { paid_on: paidOn, method } }, { onSuccess: onDone });
  }

  return (
    <form
      className="clients__form orders__invoice"
      onSubmit={handleSubmit}
      aria-label={`Cobro de la orden N° ${order.number}`}
    >
      <h4>Registrar cobro</h4>
      <label>
        Fecha del cobro
        <input type="date" value={paidOn} onChange={(event) => setPaidOn(event.target.value)} />
      </label>
      <label>
        Medio de pago
        <select value={method} onChange={(event) => setMethod(event.target.value as PaymentMethod)}>
          <option value="">Elegí</option>
          {(Object.keys(PAYMENT_METHOD_LABELS) as PaymentMethod[]).map((value) => (
            <option key={value} value={value}>
              {PAYMENT_METHOD_LABELS[value]}
            </option>
          ))}
        </select>
      </label>
      {missing && (
        <p className="clients__error" role="alert">
          Elegí la fecha y el medio de pago.
        </p>
      )}
      {payment.isError && (
        <p className="clients__error" role="alert">
          {payment.error.message}
        </p>
      )}
      <button type="submit" className="btn--primary" disabled={payment.isPending}>
        {payment.isPending ? "Guardando…" : "Registrar cobro"}
      </button>
      <button type="button" onClick={onCancel}>
        Cancelar
      </button>
    </form>
  );
}

/** Anula un cobro cargado por error, con motivo: vuelve a Facturada (E04-10, criterio 4). */
export function VoidPaymentForm({
  order,
  onDone,
  onCancel,
}: {
  order: OrderListItem;
  onDone: () => void;
  onCancel: () => void;
}) {
  const payment = usePayment(order.id);
  const [reason, setReason] = useState("");
  const [missing, setMissing] = useState(false);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!reason.trim()) {
      setMissing(true);
      return;
    }
    setMissing(false);
    payment.mutate({ kind: "void", body: { reason: reason.trim() } }, { onSuccess: onDone });
  }

  return (
    <form
      className="clients__form orders__invoice"
      onSubmit={handleSubmit}
      aria-label={`Anular el cobro de la orden N° ${order.number}`}
    >
      <h4>Anular cobro</h4>
      <label>
        Motivo
        <input value={reason} maxLength={255} onChange={(event) => setReason(event.target.value)} />
      </label>
      {missing && (
        <p className="clients__error" role="alert">
          Escribí por qué se anula el cobro.
        </p>
      )}
      {payment.isError && (
        <p className="clients__error" role="alert">
          {payment.error.message}
        </p>
      )}
      <button type="submit" className="btn--danger" disabled={payment.isPending}>
        Anular cobro
      </button>
      <button type="button" onClick={onCancel}>
        Cancelar
      </button>
    </form>
  );
}
