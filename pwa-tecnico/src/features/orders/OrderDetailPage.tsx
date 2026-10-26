import type { ReactNode } from "react";
import { Link, useParams } from "react-router-dom";

import type { components } from "../../api/schema";
import { dueLabel, statusLabel } from "./labels";
import { useOrderDetail } from "./useOrderDetail";

type OrderDetail = components["schemas"]["OrderDetailTechnicianOut"];

export function OrderDetailPage() {
  const { orderId = "" } = useParams();
  const query = useOrderDetail(orderId);

  let body: ReactNode;
  if (query.isPending) {
    body = <p className="orders__message">Cargando la orden…</p>;
  } else if (query.isError) {
    body = (
      <p className="orders__message" role="alert">
        No se pudo cargar la orden. Revisá la conexión.
      </p>
    );
  } else if (query.data === null) {
    body = (
      <div className="orders__message">
        <p>Esta orden ya no está entre las de tu escuadrilla.</p>
        <p>Puede que la hayan reasignado o cancelado. Volvé a la lista para ver las tuyas.</p>
      </div>
    );
  } else {
    body = <OrderDetail order={query.data} />;
  }

  return (
    <main className="orders">
      <Link to="/" className="order-detail__back">
        ← Mis órdenes
      </Link>
      {body}
    </main>
  );
}

function OrderDetail({ order }: { order: OrderDetail }) {
  const due = dueLabel(order.scheduled_for, order.today);
  const equipment = order.equipment
    ? [
        order.equipment.location_note,
        order.equipment.equipment_type_name,
        [order.equipment.brand, order.equipment.model].filter(Boolean).join(" "),
      ]
        .filter(Boolean)
        .join(" · ")
    : "Sin equipo";

  return (
    <article className="order-detail">
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
      <h1 className="order-detail__client">{order.client_name}</h1>

      <dl className="order-detail__facts">
        <dt>Dirección</dt>
        <dd>
          <a href={order.site.map_url} target="_blank" rel="noreferrer">
            {order.site.address}
          </a>
          {order.site.reference && (
            <span className="order-detail__reference">{order.site.reference}</span>
          )}
        </dd>
        {order.requester_area && (
          <>
            <dt>Sector</dt>
            <dd>{order.requester_area}</dd>
          </>
        )}
        {order.site.contact_names.length > 0 && (
          <>
            <dt>Contacto</dt>
            <dd>{order.site.contact_names.join(", ")}</dd>
          </>
        )}
        <dt>Equipo</dt>
        <dd>{equipment}</dd>
        <dt>Para</dt>
        <dd className={due.overdue ? "order-card__day--overdue" : undefined}>{due.text}</dd>
      </dl>

      {order.description && (
        <section className="order-detail__section">
          <h2>Indicaciones</h2>
          <p className="order-detail__notes">{order.description}</p>
        </section>
      )}

      <section className="order-detail__section">
        <h2 id="order-tasks">Tareas</h2>
        {order.tasks.length > 0 ? (
          <ul className="order-detail__tasks" aria-labelledby="order-tasks">
            {order.tasks.map((task) => (
              <li key={task}>{task}</li>
            ))}
          </ul>
        ) : (
          <p className="order-detail__empty">Este tipo de trabajo no tiene tareas cargadas.</p>
        )}
      </section>
    </article>
  );
}
