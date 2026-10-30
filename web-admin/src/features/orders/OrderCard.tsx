import { ClipboardList, MoreHorizontal } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";

import {
  BILLING_STATUS_LABELS,
  cancelReasonText,
  formatDate,
  formatDay,
  formatMoney,
  initials,
  returnedText,
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
}

const STATUS_LABELS: Record<OrderListItem["status"], string> = {
  pending: "Pendiente",
  assigned: "Asignada",
  in_progress: "En curso",
  done: "Terminada",
  invoiced: "Facturada",
  paid: "Cobrada",
  cancelled: "Cancelada",
};

/** Quién la tiene y la fecha que importa en su estado. */
function footer(order: OrderListItem): { person: string | null; who: ReactNode; when: ReactNode } {
  if (order.status === "done" && order.completed) {
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
export function OrderCard({ order, primary, more, children }: OrderCardProps) {
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
          <span className={`icon-box icon-box--${order.status}`} aria-hidden="true">
            <ClipboardList size={18} strokeWidth={1.75} />
          </span>
          <div className="order-card__heading">
            <h4>
              <span className="order-card__number">N° {order.number}</span>{" "}
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
              <span className={`badge badge--${order.status}`}>{STATUS_LABELS[order.status]}</span>
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
        {order.cancellation && (
          <p className="order-card__description">
            Motivo: <span>{cancelReasonText(order.cancellation)}</span>
          </p>
        )}
        {order.status === "done" && <BillingLine order={order} />}

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

/** Estado de cobro y total de una terminada (E04-14); sin importes, pendiente. */
function BillingLine({ order }: { order: OrderListItem }) {
  const billing = order.billing ?? null;
  const status = billing?.status ?? "pending";
  return (
    <p className={`order-card__billing order-card__billing--${status}`}>
      <span className="order-card__billing-status">{BILLING_STATUS_LABELS[status]}</span>
      <span>
        {billing ? formatMoney(billing.total) : "Sin importes"}
        {billing?.invoice_number && ` · Factura ${billing.invoice_number}`}
      </span>
    </p>
  );
}
