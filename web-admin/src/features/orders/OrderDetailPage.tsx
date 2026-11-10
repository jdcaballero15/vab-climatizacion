import { ArrowLeft } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { PageHeader } from "../../app/PageHeader";
import { ClosureDetail } from "./ClosureDetail";
import { ReceiptButtons } from "./ReceiptButtons";
import {
  CHANNEL_LABELS,
  cancelReasonText,
  formatDateTime,
  formatDay,
  ORDER_STATUS_LABELS,
  timelineLabel,
  workshopStageText,
} from "./labels";
import { OrderMaterials } from "./OrderMaterials";
import type { OrderDetail } from "./types";
import { useOrderDetail } from "./useOrders";

/**
 * Todo lo de una orden en una pantalla (E04-06): sus datos, el cierre con fotos y firma,
 * los materiales con su precio y la línea de tiempo con quién hizo cada paso y cuándo.
 */
export function OrderDetailPage() {
  const { orderId = "" } = useParams();
  const detail = useOrderDetail(orderId);

  const back = (
    <Link to="/ordenes" className="btn btn--sm">
      <ArrowLeft size={16} aria-hidden="true" />
      Órdenes
    </Link>
  );

  if (detail.isLoading) {
    return <p>Cargando la orden…</p>;
  }
  if (detail.isError || !detail.data) {
    return (
      <section>
        {back}
        <p role="alert">No se encontró la orden.</p>
      </section>
    );
  }
  const order = detail.data;
  return (
    <section className="order-detail">
      <PageHeader
        eyebrow="Operación"
        title={`Orden N° ${order.number}`}
        subtitle={`${order.client.name} · ${order.work_type_name}`}
        actions={back}
      />
      <div className="order-detail__layout">
        <div className="card order-detail__card">
          <h3>
            Datos{" "}
            <span className={`badge badge--${order.status}`}>
              {ORDER_STATUS_LABELS[order.status]}
            </span>
          </h3>
          <OrderFacts order={order} />
        </div>

        {order.has_closure && (
          <div className="card order-detail__card">
            <h3>Último cierre de la escuadrilla</h3>
            <ClosureDetail order={order} />
          </div>
        )}

        <OrderMaterials orderId={order.id} orderNumber={order.number} />

        <ReceiptButtons order={order} />

        <div className="card order-detail__card">
          <h3 id="order-timeline">Línea de tiempo</h3>
          <ol className="order-detail__timeline" aria-labelledby="order-timeline">
            {order.timeline.map((entry, index) => (
              <li key={`${entry.occurred_at}-${index}`}>
                <time>{formatDateTime(entry.occurred_at)}</time>
                <strong>{timelineLabel(entry)}</strong>
                {entry.actor_name && <span> · {entry.actor_name}</span>}
                {entry.note && <p>{entry.note}</p>}
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}

function OrderFacts({ order }: { order: OrderDetail }) {
  const site = order.site.label
    ? `${order.site.label} · ${order.site.address}`
    : order.site.address;
  const requester = [order.requester_name, order.requester_area].filter(Boolean).join(" · ");
  const rows: [string, string | null][] = [
    ["Cliente", `${order.client.name} (N° ${order.client.number})`],
    ["Domicilio", order.site.reference ? `${site} (${order.site.reference})` : site],
    ["Tipo de trabajo", order.work_type_name],
    ["Etapa", order.workshop_stage ? workshopStageText(order.workshop_stage) : null],
    [
      "Equipo",
      order.equipment
        ? `${order.equipment.internal_code} · ${order.equipment.location_note}`
        : "Sin equipo",
    ],
    [
      "Escuadrilla",
      order.assignment
        ? `${order.assignment.crew_name}, prevista para el ${formatDay(order.assignment.scheduled_for)}`
        : null,
    ],
    ["Devuelta por la oficina", order.assignment?.return_reason ?? null],
    ["Creada", formatDateTime(order.created_at)],
    ["Canal", order.channel ? CHANNEL_LABELS[order.channel] : null],
    ["Pidió", requester || null],
    ["Indicaciones", order.description],
    [
      "Cancelada",
      order.cancellation
        ? `${cancelReasonText(order.cancellation)} · ${order.cancellation.cancelled_by_name}`
        : null,
    ],
  ];
  return (
    <dl className="orders__closure" aria-label={`Datos de la orden N° ${order.number}`}>
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
