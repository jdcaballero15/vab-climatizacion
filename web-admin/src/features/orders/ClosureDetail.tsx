import {
  EQUIPMENT_CONDITION_LABELS,
  formatDate,
  NOT_DONE_REASON_LABELS,
  OUTCOME_LABELS,
} from "./labels";
import type { OrderListItem } from "./types";
import { useOrderClosure } from "./useOrders";

/** Lo que cargó la escuadrilla al cerrar, para revisarlo antes de facturar (E04-08). */
export function ClosureDetail({ order }: { order: OrderListItem }) {
  const closure = useOrderClosure(order.id);
  const label = `Cierre de la orden N° ${order.number}`;

  if (closure.isLoading) {
    return <p>Cargando el cierre…</p>;
  }
  if (closure.isError || !closure.data) {
    return <p role="alert">No se pudo cargar el cierre.</p>;
  }
  const data = closure.data;
  const rows: [string, string | null][] = [
    ["Resultado", OUTCOME_LABELS[data.outcome]],
    ["Escuadrilla", data.crew_name],
    ["Cerrada el", `${formatDate(data.closed_at)} por ${data.closed_by_name}`],
    ["Fueron", data.technicians.join(", ") || null],
    ["Tareas", data.tasks.join(", ") || null],
    ["Falla", data.failure],
    ["Reparación", data.repair],
    [
      "Estado del equipo",
      data.equipment_condition && EQUIPMENT_CONDITION_LABELS[data.equipment_condition],
    ],
    ["Motivo", data.not_done_reason && NOT_DONE_REASON_LABELS[data.not_done_reason]],
    ["Observación", data.observation],
  ];

  return (
    <dl className="orders__closure" aria-label={label}>
      {rows
        .filter((row): row is [string, string] => Boolean(row[1]))
        .map(([term, value]) => (
          <div key={term}>
            <dt>{term}</dt>
            <dd>{value}</dd>
          </div>
        ))}
    </dl>
  );
}
