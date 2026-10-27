import { Fragment, useState } from "react";

import { AssignOrderForm } from "./AssignOrderForm";
import { CancelOrderForm } from "./CancelOrderForm";
import {
  cancelReasonText,
  formatDate,
  formatDay,
  LIST_STATUS_LABELS,
  returnedText,
} from "./labels";
import { OrderForm } from "./OrderForm";
import type { ListableStatus, OrderListItem } from "./types";
import { PAGE_SIZE, useOrderList } from "./useOrders";

type RowAction = { orderId: string; kind: "assign" | "cancel" };

/** Las columnas propias de cada estado, después de número, cliente, domicilio y tipo. */
function statusColumns(status: ListableStatus): string[] {
  if (status === "pending") {
    return ["Creada"];
  }
  if (status === "cancelled") {
    return ["Motivo", "Cancelada por", "Cancelada el"];
  }
  return ["Escuadrilla", "Fecha prevista"];
}

function statusCells(order: OrderListItem, status: ListableStatus) {
  if (status === "pending") {
    return <td>{formatDate(order.created_at)}</td>;
  }
  if (status === "cancelled") {
    const cancellation = order.cancellation;
    return (
      <>
        <td>{cancellation && cancelReasonText(cancellation)}</td>
        <td>{cancellation?.cancelled_by_name}</td>
        <td>{cancellation && formatDate(cancellation.cancelled_at)}</td>
      </>
    );
  }
  return (
    <>
      <td>{order.assignment?.crew_name}</td>
      <td>{order.assignment && formatDay(order.assignment.scheduled_for)}</td>
    </>
  );
}

/**
 * Alta de órdenes y listado por estado: desde Pendientes se asignan (E04-03) y hasta En curso
 * se cancelan (E04-07). Las canceladas se consultan sin acciones.
 */
export function OrdersPage() {
  const [status, setStatus] = useState<ListableStatus>("pending");
  const [offset, setOffset] = useState(0);
  const [action, setAction] = useState<RowAction | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const page = useOrderList(status, offset);
  const total = page.data?.total ?? 0;
  const items = page.data?.items ?? [];
  const statusName = LIST_STATUS_LABELS[status].toLowerCase();
  const withActions = status !== "cancelled";
  const columns = ["Número", "Cliente", "Domicilio", "Tipo de trabajo", ...statusColumns(status)];
  const colSpan = columns.length + (withActions ? 1 : 0);

  function open(orderId: string, kind: RowAction["kind"]) {
    setNotice(null);
    setAction({ orderId, kind });
  }

  return (
    <section className="clients">
      <h2>Órdenes</h2>

      <OrderForm />

      <h3 id="orders-list-title">Órdenes {statusName}</h3>
      <div className="clients__filters">
        <label htmlFor="order-status">Estado</label>
        <select
          id="order-status"
          value={status}
          onChange={(event) => {
            setStatus(event.target.value as ListableStatus);
            setOffset(0);
            setAction(null);
            setNotice(null);
          }}
        >
          {Object.entries(LIST_STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>
      {notice && <p role="status">{notice}</p>}
      {page.isLoading && <p>Cargando órdenes…</p>}
      {page.isError && <p role="alert">No se pudieron cargar las órdenes {statusName}.</p>}
      {page.data && items.length === 0 && <p>No hay órdenes {statusName}.</p>}
      {items.length > 0 && (
        <>
          <table className="users__table" aria-labelledby="orders-list-title">
            <thead>
              <tr>
                {columns.map((column) => (
                  <th key={column}>{column}</th>
                ))}
                {withActions && <th />}
              </tr>
            </thead>
            <tbody>
              {items.map((order) => (
                <Fragment key={order.id}>
                  <tr>
                    <td>{order.number}</td>
                    <td>{order.client_name}</td>
                    <td>{order.site_label ?? order.site_address}</td>
                    <td>{order.work_type_name}</td>
                    {statusCells(order, status)}
                    {withActions && (
                      <td>
                        {order.status === "pending" && (
                          <button
                            type="button"
                            aria-label={`Asignar la orden N° ${order.number}`}
                            onClick={() => open(order.id, "assign")}
                          >
                            Asignar
                          </button>
                        )}{" "}
                        <button
                          type="button"
                          aria-label={`Cancelar la orden N° ${order.number}`}
                          onClick={() => open(order.id, "cancel")}
                        >
                          Cancelar
                        </button>
                      </td>
                    )}
                  </tr>
                  {order.returned && (
                    <tr className="orders__returned">
                      <td colSpan={colSpan}>{returnedText(order.returned)}</td>
                    </tr>
                  )}
                  {action?.orderId === order.id && (
                    <tr>
                      <td colSpan={colSpan}>
                        {action.kind === "assign" ? (
                          <AssignOrderForm
                            order={order}
                            onCancel={() => setAction(null)}
                            onAssigned={(assignment, crew) => {
                              setAction(null);
                              setNotice(
                                `Orden N° ${order.number} asignada a ${crew.name} ` +
                                  `para el ${formatDay(assignment.scheduled_for)}.`,
                              );
                            }}
                          />
                        ) : (
                          <CancelOrderForm
                            order={order}
                            onClose={() => setAction(null)}
                            onCancelled={() => {
                              setAction(null);
                              setNotice(`Orden N° ${order.number} cancelada.`);
                            }}
                          />
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>

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
        </>
      )}
    </section>
  );
}
