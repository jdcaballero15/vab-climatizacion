import { useState } from "react";

import { ClosureDetail } from "../orders/ClosureDetail";
import { formatDate, ORDER_STATUS_LABELS } from "../orders/labels";
import { useWorkTypes } from "../work-types/useWorkTypes";
import type { ClientOrder } from "./types";
import {
  HISTORY_PAGE_SIZE,
  useClientOrders,
  useEquipment,
  type HistoryFilters,
} from "./useClients";

const NO_FILTERS: HistoryFilters = { equipmentId: "", workTypeId: "", from: "", to: "" };

/**
 * Historial de órdenes en la ficha del cliente (E03-04): la más nueva primero, de a 20,
 * con filtros por equipo, tipo de trabajo y período. El cierre se ve como en Terminadas.
 */
export function ClientHistory({ clientId }: { clientId: string }) {
  const [filters, setFilters] = useState<HistoryFilters>(NO_FILTERS);
  const [offset, setOffset] = useState(0);
  const [openId, setOpenId] = useState<string | null>(null);
  const history = useClientOrders(clientId, filters, offset);
  const equipment = useEquipment(clientId, null);
  // Con los inactivos: una orden vieja puede ser de un tipo que ya no se usa.
  const workTypes = useWorkTypes(true);
  const id = (field: string) => `history-${clientId}-${field}`;
  const filtered = Object.values(filters).some(Boolean);
  const items = history.data?.items ?? [];
  const total = history.data?.total ?? 0;

  function change(next: Partial<HistoryFilters>) {
    setFilters((current) => ({ ...current, ...next }));
    setOffset(0);
    setOpenId(null);
  }

  return (
    <section className="clients__contacts" aria-labelledby={id("title")}>
      <h4 id={id("title")}>Historial</h4>
      <div className="clients__history-filters">
        <span>
          <label htmlFor={id("equipment")}>Equipo</label>
          <select
            id={id("equipment")}
            value={filters.equipmentId}
            onChange={(event) => change({ equipmentId: event.target.value })}
          >
            <option value="">Todos</option>
            {equipment.data?.map((item) => (
              <option key={item.id} value={item.id}>
                {item.internal_code} · {item.location_note}
              </option>
            ))}
          </select>
        </span>
        <span>
          <label htmlFor={id("work-type")}>Tipo de trabajo</label>
          <select
            id={id("work-type")}
            value={filters.workTypeId}
            onChange={(event) => change({ workTypeId: event.target.value })}
          >
            <option value="">Todos</option>
            {workTypes.data?.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </span>
        <span>
          <label htmlFor={id("from")}>Creadas desde</label>
          <input
            id={id("from")}
            type="date"
            value={filters.from}
            max={filters.to || undefined}
            onChange={(event) => change({ from: event.target.value })}
          />
        </span>
        <span>
          <label htmlFor={id("to")}>Hasta</label>
          <input
            id={id("to")}
            type="date"
            value={filters.to}
            min={filters.from || undefined}
            onChange={(event) => change({ to: event.target.value })}
          />
        </span>
        {filtered && (
          <button type="button" onClick={() => change(NO_FILTERS)}>
            Limpiar filtros
          </button>
        )}
      </div>

      {history.isLoading && <p className="muted">Cargando el historial…</p>}
      {history.isError && <p role="alert">No se pudo cargar el historial.</p>}
      {history.data && items.length === 0 && (
        <p className="muted">
          {filtered
            ? "Ninguna orden coincide con los filtros."
            : "Este cliente todavía no tiene órdenes."}
        </p>
      )}
      {items.length > 0 && (
        <div className="clients__history-scroll">
          <table className="users__table" aria-label="Historial de órdenes">
            <thead>
              <tr>
                <th>N°</th>
                <th>Creada</th>
                <th>Estado</th>
                <th>Tipo de trabajo</th>
                <th>Domicilio</th>
                <th>Equipo</th>
                <th>Escuadrilla</th>
                <th>Cierre</th>
              </tr>
            </thead>
            <tbody>
              {items.map((order) => (
                <HistoryRow
                  key={order.id}
                  order={order}
                  open={openId === order.id}
                  onToggle={() => setOpenId(openId === order.id ? null : order.id)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
      {total > HISTORY_PAGE_SIZE && (
        <nav className="clients__pager" aria-label="Páginas del historial">
          <button
            type="button"
            onClick={() => setOffset(Math.max(0, offset - HISTORY_PAGE_SIZE))}
            disabled={offset === 0}
          >
            Anterior
          </button>
          <span>
            {offset + 1} a {offset + items.length} de {total}
          </span>
          <button
            type="button"
            onClick={() => setOffset(offset + HISTORY_PAGE_SIZE)}
            disabled={offset + HISTORY_PAGE_SIZE >= total}
          >
            Siguiente
          </button>
        </nav>
      )}
    </section>
  );
}

interface HistoryRowProps {
  order: ClientOrder;
  open: boolean;
  onToggle: () => void;
}

function HistoryRow({ order, open, onToggle }: HistoryRowProps) {
  return (
    <>
      <tr>
        <td>{order.number}</td>
        <td>{formatDate(order.created_at)}</td>
        <td>
          <span className={`badge badge--${order.status}`}>
            {ORDER_STATUS_LABELS[order.status]}
          </span>
        </td>
        <td>{order.work_type_name}</td>
        <td>{order.site_label ?? order.site_address}</td>
        <td>{order.equipment ? order.equipment.internal_code : "-"}</td>
        <td>{order.crew_name ?? "-"}</td>
        <td>
          {order.has_closure && (
            <button
              type="button"
              className="btn--sm"
              aria-expanded={open}
              aria-label={`${open ? "Ocultar" : "Ver"} el cierre de la orden N° ${order.number}`}
              onClick={onToggle}
            >
              {open ? "Ocultar cierre" : "Ver cierre"}
            </button>
          )}
        </td>
      </tr>
      {open && (
        <tr>
          <td colSpan={8}>
            <ClosureDetail order={order} />
          </td>
        </tr>
      )}
    </>
  );
}
