import { useState } from "react";

import { formatDate } from "./labels";
import { OrderForm } from "./OrderForm";
import { PAGE_SIZE, usePendingOrders } from "./useOrders";

/** Alta de órdenes y listado de pendientes, desde donde se asignan (E04-03). */
export function OrdersPage() {
  const [offset, setOffset] = useState(0);
  const page = usePendingOrders(offset);
  const total = page.data?.total ?? 0;
  const items = page.data?.items ?? [];

  return (
    <section className="clients">
      <h2>Órdenes</h2>

      <OrderForm />

      <h3 id="pending-orders-title">Órdenes pendientes</h3>
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
              </tr>
            </thead>
            <tbody>
              {items.map((order) => (
                <tr key={order.id}>
                  <td>{order.number}</td>
                  <td>{order.client_name}</td>
                  <td>{order.site_label ?? order.site_address}</td>
                  <td>{order.work_type_name}</td>
                  <td>{formatDate(order.created_at)}</td>
                </tr>
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
