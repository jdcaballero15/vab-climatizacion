import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../../api/client";
import type { components } from "../../api/schema";
import { PageHeader } from "../../app/PageHeader";
import { formatDateTime } from "../orders/labels";
import { useUsers } from "../users/useUsers";

type AuditPage = components["schemas"]["AuditLogPage"];
type AuditLog = components["schemas"]["AuditLogOut"];

const PAGE_SIZE = 50;

const ENTITY_LABELS: Record<string, string> = {
  work_order: "Orden",
  work_order_billing: "Mano de obra",
  work_order_charge: "Otro cargo",
  invoice: "Factura",
  work_order_payment: "Cobro",
  work_type: "Tipo de trabajo",
  task: "Tarea",
  equipment_type: "Tipo de equipo",
  failure: "Falla",
  repair: "Reparación",
  part: "Material",
  part_price: "Precio",
  part_usage: "Material usado",
  client: "Cliente",
  client_site: "Domicilio",
  client_contact: "Contacto",
  equipment: "Equipo",
  crew: "Escuadrilla",
  field_technician: "Técnico",
  maintenance_plan: "Plan de mantenimiento",
  maintenance_check_step: "Paso del checklist",
  stock_location: "Ubicación de stock",
  stock_movement: "Movimiento de stock",
  app_user: "Usuario",
};

const ACTION_LABELS: Record<string, string> = {
  created: "Alta",
  updated: "Cambio",
  deactivated: "Baja",
  restored: "Restauración",
  merged: "Unificación",
  merged_in: "Recibió una unificación",
};

function changeText(log: AuditLog): string {
  if (log.note) {
    return log.note;
  }
  return Object.entries(log.changes ?? {})
    .map(([field, [before, after]]) => `${field}: ${before ?? "-"} → ${after ?? "-"}`)
    .join("; ");
}

/**
 * Auditoría de cambios (E12-01): quién cambió qué y cuándo, con las diferencias. De solo
 * lectura; los datos personales llegan enmascarados.
 */
export function AuditPage() {
  const [entity, setEntity] = useState("");
  const [actorId, setActorId] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [offset, setOffset] = useState(0);
  const users = useUsers();
  const page = useQuery<AuditPage>({
    queryKey: ["audit", { entity, actorId, from, to, offset }],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/audit", {
        params: {
          query: {
            entity: entity || undefined,
            actor_id: actorId || undefined,
            date_from: from || undefined,
            date_to: to || undefined,
            limit: PAGE_SIZE,
            offset,
          },
        },
      });
      if (error || !data) {
        throw new Error("no se pudo cargar la auditoría");
      }
      return data;
    },
    placeholderData: keepPreviousData,
  });
  const items = page.data?.items ?? [];
  const total = page.data?.total ?? 0;
  const filter = (set: (value: string) => void) => (value: string) => {
    set(value);
    setOffset(0);
  };

  return (
    <section className="catalog">
      <PageHeader
        eyebrow="Equipo"
        title="Auditoría"
        subtitle="Quién cambió qué y cuándo. De solo lectura."
      />
      <div className="orders__filters" role="group" aria-label="Filtros de la auditoría">
        <label>
          Qué
          <select value={entity} onChange={(e) => filter(setEntity)(e.target.value)}>
            <option value="">Todo</option>
            {Object.entries(ENTITY_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Usuario
          <select value={actorId} onChange={(e) => filter(setActorId)(e.target.value)}>
            <option value="">Todos</option>
            {users.data?.map((user) => (
              <option key={user.id} value={user.id}>
                {user.full_name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Desde
          <input type="date" value={from} onChange={(e) => filter(setFrom)(e.target.value)} />
        </label>
        <label>
          Hasta
          <input type="date" value={to} onChange={(e) => filter(setTo)(e.target.value)} />
        </label>
      </div>
      {page.isError && <p role="alert">No se pudo cargar la auditoría.</p>}
      {page.data && items.length === 0 && <p>No hay cambios registrados con esos filtros.</p>}
      {items.length > 0 && (
        <div className="parts__table-wrap">
          <table className="parts__table" aria-label="Cambios registrados">
            <thead>
              <tr>
                <th scope="col">Fecha</th>
                <th scope="col">Usuario</th>
                <th scope="col">Qué</th>
                <th scope="col">Acción</th>
                <th scope="col">Cambios</th>
              </tr>
            </thead>
            <tbody>
              {items.map((log) => (
                <tr key={log.id}>
                  <td>{formatDateTime(log.occurred_at)}</td>
                  <td>{log.actor_name ?? "-"}</td>
                  <td>{ENTITY_LABELS[log.entity] ?? log.entity}</td>
                  <td>{ACTION_LABELS[log.action] ?? log.action}</td>
                  <td className="audit__changes">{changeText(log)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {total > PAGE_SIZE && (
        <nav className="clients__pager" aria-label="Páginas de la auditoría">
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
    </section>
  );
}
