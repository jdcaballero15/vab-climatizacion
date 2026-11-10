import { ArrowLeft } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { PageHeader } from "../../app/PageHeader";
import { formatDate, formatDateTime, ORDER_STATUS_LABELS } from "../orders/labels";
import { useEquipmentFile } from "./useClients";

/**
 * Ficha del equipo (E03-05): datos, traslados entre clientes (E03-09) y sus trabajos, el
 * más nuevo primero, con falla, reparación y materiales (sin precios). Los anteriores a un
 * traslado y los importados de Persat se marcan.
 */
export function EquipmentFilePage() {
  const { equipmentId = "" } = useParams();
  const file = useEquipmentFile(equipmentId);

  const back = (
    <Link to="/clientes" className="btn btn--sm">
      <ArrowLeft size={16} aria-hidden="true" /> Clientes
    </Link>
  );
  if (file.isLoading) {
    return <p>Cargando ficha…</p>;
  }
  if (file.isError || !file.data) {
    return (
      <section>
        {back}
        <p role="alert">No se pudo cargar la ficha del equipo.</p>
      </section>
    );
  }
  const { equipment, transfers, orders } = file.data;

  return (
    <section className="order-detail">
      <PageHeader
        eyebrow="Equipo"
        title={`${equipment.internal_code} · ${equipment.location_note}`}
        subtitle={`${file.data.client_name} (N° ${file.data.client_number}) · ${
          file.data.site_label ?? file.data.site_address
        }`}
        actions={back}
      />
      <div className="card order-detail__card">
        <h3>Datos</h3>
        <dl className="orders__closure" aria-label="Datos del equipo">
          <dt>Tipo</dt>
          <dd>{file.data.equipment_type_name}</dd>
          {equipment.brand && (
            <>
              <dt>Marca</dt>
              <dd>{equipment.brand}</dd>
            </>
          )}
          {equipment.model && (
            <>
              <dt>Modelo</dt>
              <dd>{equipment.model}</dd>
            </>
          )}
          {equipment.serial_number && (
            <>
              <dt>Número de serie</dt>
              <dd>{equipment.serial_number}</dd>
            </>
          )}
          {equipment.deleted_at && (
            <>
              <dt>Estado</dt>
              <dd>Dado de baja el {formatDate(equipment.deleted_at)}</dd>
            </>
          )}
        </dl>
      </div>

      {transfers.length > 0 && (
        <div className="card order-detail__card">
          <h3>Traslados</h3>
          <ul aria-label="Traslados del equipo">
            {transfers.map((transfer, index) => (
              <li key={index}>
                {formatDateTime(transfer.transferred_at)}: de {transfer.from_client_name} (
                {transfer.from_code}) a {transfer.to_client_name} ({transfer.to_code}) ·{" "}
                {transfer.transferred_by_name}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="card order-detail__card">
        <h3 id="equipment-orders">Trabajos</h3>
        {orders.length === 0 && <p className="muted">Todavía no tiene trabajos.</p>}
        <ol className="order-detail__timeline" aria-labelledby="equipment-orders">
          {orders.map((order) => (
            <li key={order.id}>
              <strong>
                <Link to={`/ordenes/${order.id}`}>N° {order.number}</Link> · {order.work_type_name}{" "}
                · {ORDER_STATUS_LABELS[order.status]}
              </strong>{" "}
              <span className="muted">
                {formatDate(order.closed_at ?? order.created_at)}
                {order.before_transfer && ` · Anterior al traslado (${order.client_name})`}
                {order.imported && " · Importada de Persat"}
              </span>
              {(order.failure || order.repair) && (
                <p>
                  {order.failure && `Falla: ${order.failure}. `}
                  {order.repair && `Reparación: ${order.repair}.`}
                </p>
              )}
              {order.materials.length > 0 && <p>Materiales: {order.materials.join(", ")}</p>}
              {order.observation && <p className="muted">{order.observation}</p>}
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
