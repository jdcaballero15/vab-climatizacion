import { LogOut, MapPin, RefreshCw, Snowflake } from "lucide-react";
import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";

import type { components } from "../../api/schema";
import type { ClosedNotice } from "./ClosurePage";
import { dueLabel, statusLabel } from "./labels";
import { useMyOrders } from "./useMyOrders";

type Order = components["schemas"]["OrderTechnicianOut"];

interface MyOrdersPageProps {
  onLogout: () => void;
}

export function MyOrdersPage({ onLogout }: MyOrdersPageProps) {
  const query = useMyOrders();
  const data = query.data;
  const notice = (useLocation().state as ClosedNotice | null)?.notice;

  let title = "Mis órdenes";
  let body: ReactNode;
  if (data === undefined) {
    body = query.isError ? (
      <p className="orders__message" role="alert">
        No se pudieron cargar las órdenes. Revisá la conexión.
      </p>
    ) : (
      <p className="orders__message">Cargando las órdenes…</p>
    );
  } else if (!data.crew) {
    body = (
      <p className="orders__message">
        Este usuario no tiene una escuadrilla asignada. Avisale a administración.
      </p>
    );
  } else {
    title = data.crew.name;
    body =
      data.orders.length === 0 ? (
        <div className="orders__message">
          <p>No tienen trabajo asignado.</p>
          <p>Cuando administración les asigne una orden, aparece acá.</p>
        </div>
      ) : (
        <ul className="orders__list">
          {data.orders.map((order) => (
            <li key={order.id}>
              <OrderCard order={order} today={data.today} />
            </li>
          ))}
        </ul>
      );
  }

  const count = data?.crew ? data.orders.length : 0;

  return (
    <main className="orders">
      <header className="orders__header">
        <p className="eyebrow">Mis órdenes</p>
        <h1>{title}</h1>
        {count > 0 && (
          <p>
            {count} {count === 1 ? "orden para hacer." : "órdenes para hacer."}
          </p>
        )}
      </header>
      <div className="orders__actions">
        <button type="button" onClick={() => void query.refetch()} disabled={query.isFetching}>
          <RefreshCw size={18} aria-hidden="true" />
          Actualizar
        </button>
        <button type="button" className="orders__logout" onClick={onLogout}>
          <LogOut size={18} aria-hidden="true" />
          Cerrar sesión
        </button>
      </div>
      {notice && (
        <p className="orders__notice" role="status">
          {notice}
        </p>
      )}
      {data !== undefined && query.isError && (
        <p className="orders__warning" role="alert">
          No se pudo actualizar. Se muestra la última lista cargada.
        </p>
      )}
      {body}
    </main>
  );
}

function OrderCard({ order, today }: { order: Order; today: string }) {
  const due = dueLabel(order.scheduled_for, today);
  const equipment = order.equipment
    ? `${order.equipment.location_note} · ${order.equipment.equipment_type_name}`
    : "Sin equipo";

  return (
    <Link to={`/ordenes/${order.id}`} className="order-card-link">
      <article className={`order-card order-card--${order.status}`}>
        <div className="order-card__row">
          <span>
            <span className="order-card__number">N° {order.number}</span>
            {" · "}
            <span>{order.work_type_name}</span>
          </span>
          <span className={`order-card__status order-card__status--${order.status}`}>
            {statusLabel(order.status)}
          </span>
        </div>
        {order.description && <p className="order-card__description">{order.description}</p>}
        <div className="order-card__row">
          <span className="order-card__client">{order.client_name}</span>
          <span
            className={due.overdue ? "order-card__day order-card__day--overdue" : "order-card__day"}
          >
            {due.text}
          </span>
        </div>
        <p className="order-card__detail">
          <MapPin size={16} aria-hidden="true" />
          <span>{order.site.address}</span>
        </p>
        <p className="order-card__detail">
          <Snowflake size={16} aria-hidden="true" />
          <span>{equipment}</span>
        </p>
      </article>
    </Link>
  );
}
