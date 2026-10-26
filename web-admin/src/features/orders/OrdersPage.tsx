import { Fragment, useState } from "react";

import { AssignOrderForm } from "./AssignOrderForm";
import { formatDate, formatDay } from "./labels";
import { OrderForm } from "./OrderForm";
import { PAGE_SIZE, usePendingOrders } from "./useOrders";

/** Alta de órdenes y listado de pendientes, desde donde se asignan (E04-03). */
export function OrdersPage() {
  const [offset, setOffset] = useState(0);
  const [assigningId, setAssigningId] = useState<string | null>(null);
  const [assigned, setAssigned] = useState<string | null>(null);
  const page = usePendingOrders(offset);
  const total = page.data?.total ?? 0;
  const items = page.data?.items ?? [];

  return (
    <section className="clients">
      <h2>Órdenes</h2>

      <OrderForm />

      <h3 id="pending-orders-title">Órdenes pendientes</h3>
      {assigned && <p role="status">{assigned}</p>}
      {page.isLoading && <p>Cargando órdenes…</p>}
      {page.isError && <p role="alert">No se pudieron cargar las órdenes pendientes.</p>}
      {page.data && items.length === 0 && <p>No hay órdenes pendientes.</p>}
      {items.length > 0 && (
        <>
          <table className="users__table" aria-labelledby="pending-orders-title">
            <thead>
              <tr>
                <th>Número</th>
                <th>Cliente</th>
                <th>Domicilio</th>
                <th>Tipo de trabajo</th>
                <th>Creada</th>
                <th />
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
                    <td>{formatDate(order.created_at)}</td>
                    <td>
                      <button
                        type="button"
                        aria-label={`Asignar la orden N° ${order.number}`}
                        onClick={() => {
                          setAssigned(null);
                          setAssigningId(order.id);
                        }}
                      >
                        Asignar
                      </button>
                    </td>
                  </tr>
                  {assigningId === order.id && (
                    <tr>
                      <td colSpan={6}>
                        <AssignOrderForm
                          order={order}
                          onCancel={() => setAssigningId(null)}
                          onAssigned={(assignment, technician) => {
                            setAssigningId(null);
                            setAssigned(
                              `Orden N° ${order.number} asignada a ${technician.full_name} ` +
                                `para el ${formatDay(assignment.scheduled_for)}.`,
                            );
                          }}
                        />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>

          <nav className="clients__pager" aria-label="Páginas de órdenes pendientes">
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
