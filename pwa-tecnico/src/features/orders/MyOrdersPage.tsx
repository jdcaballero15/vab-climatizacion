import { LogOut, MapPin, RefreshCw, Snowflake } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";

import type { components } from "../../api/schema";
import type { StoredClosure } from "./closureDrafts";
import type { ClosedNotice } from "./ClosurePage";
import { dueLabel, statusLabel } from "./labels";
import { useStoredClosures } from "./useClosureDrafts";
import { useMyOrders } from "./useMyOrders";

type Order = components["schemas"]["OrderTechnicianOut"];

interface MyOrdersPageProps {
  /** Usuario de la sesión, para encontrar sus borradores (E05-13). */
  userId: string;
  onLogout: () => void;
}

export function MyOrdersPage({ userId, onLogout }: MyOrdersPageProps) {
  const query = useMyOrders();
  const loaded = useStoredClosures(userId);
  const stored = loaded ?? [];
  const [confirmingLogout, setConfirmingLogout] = useState(false);
  const data = query.data;
  const state = useLocation().state as ClosedNotice | null;
  // El cierre que había quedado pendiente ya no está guardado: el reintento lo mandó.
  const sent =
    state?.pending &&
    loaded !== undefined &&
    !loaded.some((closure) => closure.orderId === state.orderId);
  const notice = sent ? state.sentNotice : state?.notice;
  const closureOf = new Map(stored.map((closure) => [closure.orderId, closure]));
  // Cierres guardados de órdenes que no están en la lista (la oficina las canceló o
  // reasignó, o ya se cerraron) o de todas, si la lista no se pudo cargar.
  const listed = new Set(data?.crew ? data.orders.map((order) => order.id) : []);
  const unlisted =
    data?.crew || (data === undefined && (query.isError || query.isPaused))
      ? stored.filter((closure) => !listed.has(closure.orderId))
      : [];

  let title = "Mis órdenes";
  let body: ReactNode;
  if (data === undefined) {
    // Sin señal TanStack Query pausa la consulta en lugar de fallar: se avisa (ADR 0009).
    body = query.isPaused ? (
      <p className="orders__message" role="alert">
        No hay señal. Las órdenes se cargan cuando vuelva la conexión.
      </p>
    ) : query.isError ? (
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
              <OrderCard order={order} today={data.today} closure={closureOf.get(order.id)} />
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
        <button
          type="button"
          className="orders__logout"
          // E05-13, criterio 9: con un cierre sin enviar, primero se avisa.
          onClick={() => (stored.length > 0 ? setConfirmingLogout(true) : onLogout())}
        >
          <LogOut size={18} aria-hidden="true" />
          Cerrar sesión
        </button>
      </div>
      {confirmingLogout && (
        <LogoutWarning
          count={stored.length}
          onConfirm={onLogout}
          onCancel={() => setConfirmingLogout(false)}
        />
      )}
      {notice && (
        <p
          className={
            state?.pending && !sent ? "orders__notice orders__notice--pending" : "orders__notice"
          }
          role="status"
        >
          {notice}
        </p>
      )}
      {data !== undefined && query.isError && (
        <p className="orders__warning" role="alert">
          No se pudo actualizar. Se muestra la última lista cargada.
        </p>
      )}
      {unlisted.length > 0 && <UnlistedClosures closures={unlisted} />}
      {body}
    </main>
  );
}

const CLOSURE_LABEL = {
  draft: "Borrador",
  pending: "Pendiente de enviar",
  rejected: "Rechazado",
} as const;

/** Etiqueta del cierre guardado en el celular (E05-13, criterio 2). */
function ClosureBadge({ closure }: { closure: StoredClosure }) {
  // Un 422 de un envío anterior: hay que abrirlo y corregir el campo marcado.
  const label =
    closure.status === "draft" && closure.problem ? "Revisar" : CLOSURE_LABEL[closure.status];
  return <span className={`order-card__draft order-card__draft--${closure.status}`}>{label}</span>;
}

function UnlistedClosures({ closures }: { closures: StoredClosure[] }) {
  return (
    <section className="orders__saved" aria-labelledby="orders-saved-title">
      <h2 id="orders-saved-title" className="orders__saved-title">
        Guardados en este celular
      </h2>
      <ul className="orders__list">
        {closures.map((closure) => (
          <li key={closure.orderId}>
            <Link to={`/ordenes/${closure.orderId}/cerrar`} className="order-card-link">
              <article className={`order-card order-card--saved order-card--${closure.status}`}>
                <div className="order-card__row">
                  <span>
                    <span className="order-card__number">
                      {closure.order ? `N° ${closure.order.number}` : "Orden"}
                    </span>
                    {closure.order && ` · ${closure.order.workTypeName}`}
                  </span>
                  <ClosureBadge closure={closure} />
                </div>
                {closure.order && (
                  <div className="order-card__row">
                    <span className="order-card__client">{closure.order.clientName}</span>
                  </div>
                )}
              </article>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

interface LogoutWarningProps {
  count: number;
  onConfirm: () => void;
  onCancel: () => void;
}

/** El borrador no se borra al salir: queda para cuando vuelva a entrar el mismo usuario. */
function LogoutWarning({ count, onConfirm, onCancel }: LogoutWarningProps) {
  return (
    <div
      className="order-start order-start--confirm orders__logout-warning"
      role="group"
      aria-label="Confirmar cierre de sesión"
    >
      <p className="order-start__question">
        {count === 1 ? "Hay un cierre sin enviar." : `Hay ${count} cierres sin enviar.`}
      </p>
      <p className="orders__logout-hint">
        Queda guardado en este celular y aparece cuando vuelvas a entrar con este usuario.
      </p>
      <div className="order-start__actions">
        <button type="button" className="order-start__primary" onClick={onConfirm}>
          Cerrar sesión igual
        </button>
        <button type="button" className="order-start__secondary" onClick={onCancel}>
          Cancelar
        </button>
      </div>
    </div>
  );
}

interface OrderCardProps {
  order: Order;
  today: string;
  /** Cierre empezado o pendiente en este celular (E05-13, criterio 2). */
  closure: StoredClosure | undefined;
}

function OrderCard({ order, today, closure }: OrderCardProps) {
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
          <span className="order-card__badges">
            {closure && <ClosureBadge closure={closure} />}
            <span className={`order-card__status order-card__status--${order.status}`}>
              {statusLabel(order.status)}
            </span>
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
