import { ChevronLeft } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import type { components } from "../../api/schema";
import { dueLabel, statusLabel } from "./labels";
import { useOrderDetail } from "./useOrderDetail";
import { useStartOrder } from "./useStartOrder";

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
        <ChevronLeft size={20} aria-hidden="true" />
        Mis órdenes
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
      {order.status === "assigned" && <StartOrder order={order} />}
      {order.status === "in_progress" && (
        <Link to={`/ordenes/${order.id}/cerrar`} className="order-close">
          Cerrar orden
        </Link>
      )}

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

/**
 * Botones "Iniciar" y "Ya la terminé" con confirmación dentro de la app (sin diálogos del
 * navegador). "Ya la terminé" es para cuando se olvidaron de iniciarla: la inicia y abre
 * el cierre.
 */
function StartOrder({ order }: { order: OrderDetail }) {
  const [confirming, setConfirming] = useState<"start" | "finish" | null>(null);
  const start = useStartOrder(order.id);
  const navigate = useNavigate();

  if (confirming === null) {
    return (
      <div className="order-start">
        <div className="order-start__actions">
          <button
            type="button"
            className="order-start__primary"
            onClick={() => {
              start.reset();
              setConfirming("start");
            }}
          >
            Iniciar
          </button>
          <button
            type="button"
            className="order-start__secondary"
            onClick={() => {
              start.reset();
              setConfirming("finish");
            }}
          >
            Ya la terminé
          </button>
        </div>
        {start.isError && (
          <p className="order-start__error" role="alert">
            No se pudo iniciar la orden. Revisá la conexión e intentá de nuevo.
          </p>
        )}
      </div>
    );
  }

  const finishing = confirming === "finish";
  return (
    <div className="order-start order-start--confirm" role="group" aria-label="Confirmar inicio">
      <p className="order-start__question">
        {finishing
          ? `¿La orden N° ${order.number} ya está hecha? Se marca iniciada y pasás al cierre.`
          : `¿Empezar la orden N° ${order.number}?`}
      </p>
      <div className="order-start__actions">
        <button
          type="button"
          className="order-start__primary"
          disabled={start.isPending}
          onClick={() =>
            start.mutate(undefined, {
              onSuccess: (data) => {
                // Con null la orden ya no es de la escuadrilla: el detalle lo avisa.
                if (finishing && data) {
                  navigate(`/ordenes/${order.id}/cerrar`);
                }
              },
              onError: () => setConfirming(null),
            })
          }
        >
          {start.isPending ? "Iniciando…" : finishing ? "Sí, cerrarla" : "Sí, empezar"}
        </button>
        <button
          type="button"
          className="order-start__secondary"
          disabled={start.isPending}
          onClick={() => setConfirming(null)}
        >
          Cancelar
        </button>
      </div>
    </div>
  );
}
