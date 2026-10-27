import {
  Activity,
  CalendarClock,
  CircleCheck,
  CircleX,
  Inbox,
  Plus,
  type LucideIcon,
} from "lucide-react";
import { useState } from "react";

import { PageHeader } from "../../app/PageHeader";
import { useCrews } from "../crews/useCrews";
import { AssignOrderForm, type AssignMode } from "./AssignOrderForm";
import { CancelOrderForm } from "./CancelOrderForm";
import { ClosureDetail } from "./ClosureDetail";
import { formatDay, initials, LIST_STATUS_LABELS } from "./labels";
import { OrderCard, type CardAction } from "./OrderCard";
import { OrderForm } from "./OrderForm";
import { UnassignOrderForm } from "./UnassignOrderForm";
import type { ListableStatus, OrderListItem } from "./types";
import { PAGE_SIZE, useOrderCounts, useOrderList } from "./useOrders";

type RowAction = {
  orderId: string;
  kind: AssignMode | "unassign" | "cancel" | "closure";
};

const ASSIGNED_WORD: Record<AssignMode, string> = {
  assign: "asignada",
  reprogram: "reprogramada",
  reassign: "reasignada",
};

const STATUSES: { status: ListableStatus; icon: LucideIcon; hint: string }[] = [
  { status: "pending", icon: Inbox, hint: "Sin escuadrilla" },
  { status: "assigned", icon: CalendarClock, hint: "Esperando a la escuadrilla" },
  { status: "in_progress", icon: Activity, hint: "La escuadrilla está trabajando" },
  { status: "done", icon: CircleCheck, hint: "Cerradas, para revisar" },
  { status: "cancelled", icon: CircleX, hint: "No se van a hacer" },
];
const KPI_STATUSES = STATUSES.filter(({ status }) => status !== "cancelled");

/** La acción más común de cada estado va a la vista; el resto, al menú de tres puntos. */
function cardActions(
  order: OrderListItem,
  status: ListableStatus,
  current: RowAction | null,
  open: (kind: RowAction["kind"]) => void,
  close: () => void,
): { primary?: CardAction; more: CardAction[] } {
  const n = `la orden N° ${order.number}`;
  const cancel: CardAction = {
    label: "Cancelar orden",
    name: `Cancelar ${n}`,
    onClick: () => open("cancel"),
    danger: true,
  };
  if (status === "done") {
    const showing = current?.orderId === order.id && current.kind === "closure";
    return {
      primary: {
        label: showing ? "Ocultar cierre" : "Ver cierre",
        name: `Ver el cierre de ${n}`,
        onClick: showing ? close : () => open("closure"),
        expanded: showing,
      },
      more: [],
    };
  }
  if (status === "cancelled") {
    return { more: [] };
  }
  if (order.status === "pending") {
    return order.returned
      ? {
          primary: {
            label: "Reprogramar",
            name: `Reprogramar ${n}`,
            onClick: () => open("reprogram"),
          },
          more: [cancel],
        }
      : {
          primary: { label: "Asignar", name: `Asignar ${n}`, onClick: () => open("assign") },
          more: [cancel],
        };
  }
  const reassign: CardAction = {
    label: "Reasignar",
    name: `Reasignar ${n}`,
    onClick: () => open("reassign"),
  };
  if (order.status === "assigned") {
    return {
      primary: reassign,
      more: [
        { label: "Desasignar", name: `Desasignar ${n}`, onClick: () => open("unassign") },
        cancel,
      ],
    };
  }
  return { primary: reassign, more: [cancel] };
}

/**
 * Alta de órdenes y listado por estado: desde Pendientes se asignan (E04-03) o reprograman,
 * Asignadas y En curso se reasignan, y las Asignadas se desasignan (E04-04). Hasta En curso
 * se cancelan (E04-07). De las terminadas se ve el cierre (E04-08); las canceladas se
 * consultan sin acciones.
 */
export function OrdersPage() {
  const [status, setStatus] = useState<ListableStatus>("pending");
  const [offset, setOffset] = useState(0);
  const [action, setAction] = useState<RowAction | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const page = useOrderList(status, offset);
  const counts = useOrderCounts(STATUSES.map((item) => item.status));
  const crews = useCrews(false);
  const total = page.data?.total ?? 0;
  const items = page.data?.items ?? [];
  const statusName = LIST_STATUS_LABELS[status].toLowerCase();

  function choose(next: ListableStatus) {
    setStatus(next);
    setOffset(0);
    setAction(null);
    setNotice(null);
  }

  function panel(order: OrderListItem) {
    if (action?.orderId !== order.id) {
      return undefined;
    }
    const close = () => setAction(null);
    if (action.kind === "closure") {
      return <ClosureDetail order={order} />;
    }
    if (action.kind === "unassign") {
      return (
        <UnassignOrderForm
          order={order}
          onClose={close}
          onUnassigned={() => {
            close();
            setNotice(`Orden N° ${order.number} desasignada: volvió a Pendientes.`);
          }}
        />
      );
    }
    if (action.kind === "cancel") {
      return (
        <CancelOrderForm
          order={order}
          onClose={close}
          onCancelled={() => {
            close();
            setNotice(`Orden N° ${order.number} cancelada.`);
          }}
        />
      );
    }
    const mode = action.kind;
    return (
      <AssignOrderForm
        order={order}
        mode={mode}
        onCancel={close}
        onAssigned={(assignment, crew) => {
          close();
          setNotice(
            `Orden N° ${order.number} ${ASSIGNED_WORD[mode]} a ${crew.name} ` +
              `para el ${formatDay(assignment.scheduled_for)}.`,
          );
        }}
      />
    );
  }

  return (
    <section className="orders">
      <PageHeader
        eyebrow="Operación"
        title="Órdenes"
        subtitle="Del pedido del cliente al cierre de la escuadrilla."
        actions={
          <button
            type="button"
            className={creating ? undefined : "btn--primary"}
            aria-expanded={creating}
            onClick={() => setCreating((open) => !open)}
          >
            {creating ? (
              "Cerrar"
            ) : (
              <>
                <Plus size={16} aria-hidden="true" />
                Nueva orden
              </>
            )}
          </button>
        }
      />

      {creating && <OrderForm />}

      <div className="kpis">
        {KPI_STATUSES.map(({ status: kpi, hint }) => (
          <div
            key={kpi}
            className={kpi === "pending" ? "card kpi kpi--accent" : "card kpi"}
            aria-label={`${LIST_STATUS_LABELS[kpi]}: ${counts[kpi] ?? "cargando"}`}
          >
            <p className="eyebrow">{LIST_STATUS_LABELS[kpi]}</p>
            <p className="kpi__value">{counts[kpi] ?? "…"}</p>
            <p className="kpi__hint">{hint}</p>
          </div>
        ))}
      </div>

      <div className="orders__layout">
        <aside className="orders__aside">
          <nav className="card status-nav" aria-label="Estados de las órdenes">
            {STATUSES.map(({ status: item, icon: Icon, hint }) => (
              <button
                key={item}
                type="button"
                className={
                  item === status ? "status-nav__item status-nav__item--active" : "status-nav__item"
                }
                aria-label={LIST_STATUS_LABELS[item]}
                aria-pressed={item === status}
                onClick={() => choose(item)}
              >
                <span className="icon-box" aria-hidden="true">
                  <Icon size={16} strokeWidth={1.75} />
                </span>
                <span className="status-nav__text">
                  <strong>{LIST_STATUS_LABELS[item]}</strong>
                  <small>{hint}</small>
                </span>
                <span className="status-nav__count">{counts[item] ?? ""}</span>
              </button>
            ))}
          </nav>

          <section className="card crews-card" aria-label="Escuadrillas activas">
            <p className="eyebrow">Escuadrillas</p>
            {crews.data?.length === 0 && <p className="muted">No hay escuadrillas activas.</p>}
            <ul>
              {crews.data?.map((crew) => (
                <li key={crew.id}>
                  <span className="avatar" aria-hidden="true">
                    {initials(crew.name)}
                  </span>
                  <span>
                    <strong>{crew.name}</strong>
                    <small>{crew.app_user ? crew.app_user.full_name : "Sin celular"}</small>
                  </span>
                </li>
              ))}
            </ul>
          </section>
        </aside>

        <div className="orders__main">
          <div className="orders__list-header">
            <h3 id="orders-list-title">Órdenes {statusName}</h3>
            {page.data && <span className="muted">{total} en total</span>}
          </div>
          {notice && <p role="status">{notice}</p>}
          {page.isLoading && <p className="muted">Cargando órdenes…</p>}
          {page.isError && <p role="alert">No se pudieron cargar las órdenes {statusName}.</p>}
          {page.data && items.length === 0 && (
            <div className="card orders__empty">No hay órdenes {statusName}.</div>
          )}
          {items.length > 0 && (
            <>
              <ul className="order-grid" aria-labelledby="orders-list-title">
                {items.map((order) => {
                  const { primary, more } = cardActions(
                    order,
                    status,
                    action,
                    (kind) => {
                      setNotice(null);
                      setAction({ orderId: order.id, kind });
                    },
                    () => setAction(null),
                  );
                  return (
                    <OrderCard key={order.id} order={order} primary={primary} more={more}>
                      {panel(order)}
                    </OrderCard>
                  );
                })}
              </ul>

              {total > PAGE_SIZE && (
                <nav className="clients__pager" aria-label={`Páginas de órdenes ${statusName}`}>
                  <button
                    type="button"
                    onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                    disabled={offset === 0}
                  >
                    Anterior
                  </button>
                  <span>
                    {offset + 1} a {offset + items.length} de {total}
                  </span>
                  <button
                    type="button"
                    onClick={() => setOffset(offset + PAGE_SIZE)}
                    disabled={offset + PAGE_SIZE >= total}
                  >
                    Siguiente
                  </button>
                </nav>
              )}
            </>
          )}
        </div>
      </div>
    </section>
  );
}
