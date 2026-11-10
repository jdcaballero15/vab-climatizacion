import { ClipboardList, MoreHorizontal } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";

import {
  cancelReasonText,
  formatDate,
  formatDay,
  formatMoney,
  initials,
  ORDER_STATUS_LABELS,
  PAYMENT_METHOD_LABELS,
  returnedText,
  workshopStageText,
} from "./labels";
import type { OrderListItem } from "./types";

export interface CardAction {
  /** Texto del botón. */
  label: string;
  /** Nombre accesible, con el número de la orden ("Asignar la orden N° 7"). */
  name: string;
  onClick: () => void;
  danger?: boolean;
  expanded?: boolean;
}

interface OrderCardProps {
  order: OrderListItem;
  /** La acción más común del estado, a la vista. */
  primary?: CardAction;
  /** El resto, en el menú de tres puntos. */
  more: CardAction[];
  /** Formulario o detalle abierto debajo de la tarjeta. */
  children?: ReactNode;
  /** Casilla para elegirla, por ejemplo para facturar varias juntas (E04-09). */
  selection?: { checked: boolean; onChange: (checked: boolean) => void };
}

const CLOSED = new Set<OrderListItem["status"]>(["done", "invoiced", "paid"]);

/** Quién la tiene y la fecha que importa en su estado. */
function footer(order: OrderListItem): { person: string | null; who: ReactNode; when: ReactNode } {
  if (CLOSED.has(order.status) && order.completed) {
    return {
      person: order.completed.crew_name,
      who: order.completed.crew_name ?? "Sin escuadrilla",
      when: (
        <>
          Cerrada <time>{formatDate(order.completed.closed_at)}</time>
        </>
      ),
    };
  }
  if (order.status === "cancelled" && order.cancellation) {
    return {
      person: order.cancellation.cancelled_by_name,
      who: <span>{order.cancellation.cancelled_by_name}</span>,
      when: (
        <>
          Cancelada <time>{formatDate(order.cancellation.cancelled_at)}</time>
        </>
      ),
    };
  }
  if (order.assignment) {
    return {
      person: order.assignment.crew_name,
      who: order.assignment.crew_name,
      when: (
        <>
          Prevista <time>{formatDay(order.assignment.scheduled_for)}</time>
        </>
      ),
    };
  }
  return {
    person: null,
    who: "Sin escuadrilla",
    when: (
      <>
        Creada <time>{formatDate(order.created_at)}</time>
      </>
    ),
  };
}

/** Una orden del listado: número y cliente, metadatos, descripción, quién la tiene y cuándo. */
export function OrderCard({ order, primary, more, children, selection }: OrderCardProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const { person, who, when } = footer(order);
  const title = `Orden N° ${order.number}`;

  useEffect(() => {
    if (!menuOpen) {
      return undefined;
    }
    function close(event: MouseEvent) {
      if (!menuRef.current?.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }
    function escape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", escape);
    };
  }, [menuOpen]);

  return (
    <li className={children ? "order-card-wrap order-card-wrap--open" : "order-card-wrap"}>
      <article className="card order-card" aria-label={title}>
        <div className="order-card__top">
          {selection && (
            <input
              type="checkbox"
              className="order-card__select"
              checked={selection.checked}
              onChange={(event) => selection.onChange(event.target.checked)}
              aria-label={`Elegir la orden N° ${order.number} para facturar`}
            />
          )}
          <span className={`icon-box icon-box--${order.status}`} aria-hidden="true">
            <ClipboardList size={18} strokeWidth={1.75} />
          </span>
          <div className="order-card__heading">
            <h4>
              {/* E04-06: el número abre el detalle con la línea de tiempo. */}
              <Link
                to={`/ordenes/${order.id}`}
                className="order-card__number"
                aria-label={`Ver el detalle de la orden N° ${order.number}`}
              >
                N° {order.number}
              </Link>{" "}
              <span>{order.client_name}</span>
            </h4>
            <p className="order-card__meta">
              <span>{order.work_type_name}</span>
              <span>{order.site_label ?? order.site_address}</span>
              {order.equipment && (
                <span title={order.equipment.location_note}>
                  Equipo {order.equipment.internal_code} · {order.equipment.location_note}
                </span>
              )}
              {order.maintenance && (
                <span className="badge badge--maintenance">
                  Mantenimiento · para el {formatDay(order.maintenance.due_on)}
                </span>
              )}
              {order.workshop_stage && (
                <span className="badge badge--workshop">
                  {workshopStageText(order.workshop_stage)}
                </span>
              )}
              <span className={`badge badge--${order.status}`}>
                {ORDER_STATUS_LABELS[order.status]}
              </span>
            </p>
          </div>
          <div className="order-card__actions" ref={menuRef}>
            {primary && (
              <button
                type="button"
                className="btn--sm"
                aria-label={primary.name}
                aria-expanded={primary.expanded}
                onClick={() => {
                  setMenuOpen(false);
                  primary.onClick();
                }}
              >
                {primary.label}
              </button>
            )}
            {more.length > 0 && (
              <button
                type="button"
                className="btn--ghost btn--sm order-card__kebab"
                aria-label={`Más acciones de la orden N° ${order.number}`}
                aria-expanded={menuOpen}
                onClick={() => setMenuOpen((open) => !open)}
              >
                <MoreHorizontal size={16} aria-hidden="true" />
              </button>
            )}
            {menuOpen && (
              <div className="order-card__menu card">
                {more.map((item) => (
                  <button
                    key={item.name}
                    type="button"
                    className={item.danger ? "btn--ghost btn--danger" : "btn--ghost"}
                    aria-label={item.name}
                    onClick={() => {
                      setMenuOpen(false);
                      item.onClick();
                    }}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {order.description && <p className="order-card__description">{order.description}</p>}
        {order.returned && <p className="order-card__returned">{returnedText(order.returned)}</p>}
        {order.assignment?.return_reason && (
          <p className="order-card__returned">
            Devuelta por la oficina: {order.assignment.return_reason}
          </p>
        )}
        {order.cancellation && (
          <p className="order-card__description">
            Motivo: <span>{cancelReasonText(order.cancellation)}</span>
          </p>
        )}
        {CLOSED.has(order.status) && <BillingLine order={order} />}

        <div className="order-card__footer">
          <span className="order-card__who">
            <span
              className={person ? "avatar" : "avatar avatar--muted"}
              aria-hidden="true"
              title={person ?? undefined}
            >
              {person ? initials(person) : "·"}
            </span>
            {typeof who === "string" ? <span>{who}</span> : who}
          </span>
          <span className="order-card__when">{when}</span>
        </div>

        {children && <div className="order-card__panel">{children}</div>}
      </article>
    </li>
  );
}

/** Total, factura y cobro de una cerrada (E04-09 a E04-11). Una terminada hace más de
 * una semana sin facturar se destaca (E04-05, criterio 4). */
function BillingLine({ order }: { order: OrderListItem }) {
  const billing = order.billing ?? null;
  const state = order.billing_overdue ? "overdue" : order.status;
  let text = "Sin facturar";
  if (order.billing_overdue) {
    text = "Terminada sin facturar hace más de una semana";
  } else if (billing?.payment) {
    text = `Cobrada el ${formatDay(billing.payment.paid_on)} · ${
      PAYMENT_METHOD_LABELS[billing.payment.method]
    }`;
  } else if (billing?.invoice) {
    text = `Factura ${billing.invoice.number} del ${formatDay(billing.invoice.issued_on)}`;
  }
  return (
    <p className={`order-card__billing order-card__billing--${state}`}>
      <span className="order-card__billing-status">{text}</span>
      <span>{billing ? formatMoney(billing.total) : "Sin importes"}</span>
    </p>
  );
}
