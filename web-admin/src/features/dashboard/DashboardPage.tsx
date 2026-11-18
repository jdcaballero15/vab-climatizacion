import { Link, useSearchParams } from "react-router-dom";

import { PageHeader } from "../../app/PageHeader";
import { useCrews } from "../crews/useCrews";
import { useEquipmentTypes } from "../equipment-types/useEquipmentTypes";
import { formatDate, formatDay, formatMoney } from "../orders/labels";
import { useWorkTypes } from "../work-types/useWorkTypes";
import { Ranking, WeeklyChart } from "./charts";
import { useDashboard, type DashboardFilters } from "./useDashboard";

const FILTER_KEYS: (keyof DashboardFilters)[] = [
  "date_from",
  "date_to",
  "client_id",
  "crew_id",
  "work_type_id",
  "equipment_type_id",
  "compare_from",
  "compare_to",
];

function difference(now: number, before: number): string {
  const delta = now - before;
  return delta === 0 ? "igual" : delta > 0 ? `+${delta}` : `${delta}`;
}

function quantity(value: string | null | undefined): string {
  return Number(value ?? 0).toLocaleString("es-AR", { maximumFractionDigits: 3 });
}

/**
 * Tablero (E10): órdenes por estado y su evolución, trabajos por técnico, fallas y
 * reparaciones más comunes, mantenimiento, terminadas sin facturar y materiales más usados.
 * Todos los indicadores usan los mismos filtros, que viajan en la dirección web para
 * compartirlos. Responsive: se usa desde el celular (E10-07).
 */
export function DashboardPage() {
  const [params, setParams] = useSearchParams();
  const filters: DashboardFilters = Object.fromEntries(
    FILTER_KEYS.flatMap((key) => (params.get(key) ? [[key, params.get(key) as string]] : [])),
  );
  const dashboard = useDashboard(filters);
  const crews = useCrews(false);
  const workTypes = useWorkTypes(false);
  const equipmentTypes = useEquipmentTypes(false);
  const data = dashboard.data;

  function set(key: keyof DashboardFilters, value: string) {
    const next = new URLSearchParams(params);
    if (value) {
      next.set(key, value);
    } else {
      next.delete(key);
    }
    setParams(next, { replace: true });
  }

  const select = (
    label: string,
    key: keyof DashboardFilters,
    options: { id: string; name: string }[] | undefined,
  ) => (
    <label>
      {label}
      <select value={filters[key] ?? ""} onChange={(event) => set(key, event.target.value)}>
        <option value="">Todos</option>
        {options?.map((option) => (
          <option key={option.id} value={option.id}>
            {option.name}
          </option>
        ))}
      </select>
    </label>
  );

  return (
    <section className="dashboard">
      <PageHeader
        eyebrow="Seguimiento"
        title="Tablero"
        subtitle={
          data ? `Del ${formatDay(data.date_from)} al ${formatDay(data.date_to)}` : "Cargando…"
        }
      />
      <div className="orders__filters" role="group" aria-label="Filtros del tablero">
        <label>
          Desde
          <input
            type="date"
            value={filters.date_from ?? data?.date_from ?? ""}
            onChange={(event) => set("date_from", event.target.value)}
          />
        </label>
        <label>
          Hasta
          <input
            type="date"
            value={filters.date_to ?? data?.date_to ?? ""}
            onChange={(event) => set("date_to", event.target.value)}
          />
        </label>
        {select("Escuadrilla", "crew_id", crews.data)}
        {select("Tipo de trabajo", "work_type_id", workTypes.data)}
        {select("Tipo de equipo", "equipment_type_id", equipmentTypes.data)}
        <label>
          Comparar desde
          <input
            type="date"
            value={filters.compare_from ?? ""}
            onChange={(event) => set("compare_from", event.target.value)}
          />
        </label>
        <label>
          hasta
          <input
            type="date"
            value={filters.compare_to ?? ""}
            onChange={(event) => set("compare_to", event.target.value)}
          />
        </label>
      </div>

      {dashboard.isError && <p role="alert">No se pudo cargar el tablero.</p>}
      {data && (
        <>
          <div className="dashboard__grid">
            <section className="card dashboard__card" aria-label="Evolución">
              <h3>Evolución por semana</h3>
              <p className="muted">
                {data.totals.created} creadas y {data.totals.done} terminadas en el período
                {data.compare &&
                  ` (contra ${data.compare.created} y ${data.compare.done}: ${difference(
                    data.totals.created,
                    data.compare.created,
                  )} y ${difference(data.totals.done, data.compare.done)})`}
                .
              </p>
              <WeeklyChart weeks={data.weeks} />
            </section>
            <section className="card dashboard__card" aria-label="Gasto en materiales">
              <h3>Gasto en materiales</h3>
              <p className="dashboard__hero">{formatMoney(data.parts_cost.total)}</p>
              <p className="muted">
                En los cierres del período, con el precio de cada orden: el aprobado o, si todavía
                no se aprobó, el de la lista.
              </p>
              <Ranking
                items={data.parts_cost.items.map((p) => ({
                  ...p,
                  value: Number(p.amount),
                  display: formatMoney(p.amount),
                }))}
                empty="Sin materiales con precio en el período."
              />
              {data.parts_cost.unpriced > 0 && (
                <p className="muted">
                  {data.parts_cost.unpriced === 1
                    ? "1 material usado no tiene precio en la lista y no suma."
                    : `${data.parts_cost.unpriced} materiales usados no tienen precio en la lista y no suman.`}{" "}
                  <Link to="/catalogos/materiales">Cargar precios</Link>
                </p>
              )}
            </section>
            <section className="card dashboard__card" aria-label="Sin facturar">
              <h3>Terminadas sin facturar</h3>
              {data.unbilled.length === 0 ? (
                <p className="muted">No hay trabajos terminados sin facturar.</p>
              ) : (
                <table className="parts__table">
                  <thead>
                    <tr>
                      <th scope="col">Orden</th>
                      <th scope="col">Cliente</th>
                      <th scope="col">Cerrada</th>
                      <th scope="col">Días</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.unbilled.map((order) => (
                      <tr key={order.id}>
                        <td>
                          <Link to={`/ordenes/${order.id}`}>N° {order.number}</Link>
                        </td>
                        <td>{order.client_name}</td>
                        <td>{order.closed_at ? formatDate(order.closed_at) : "-"}</td>
                        <td>{order.days ?? "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
            <section className="card dashboard__card" aria-label="Materiales más usados">
              <h3>Materiales más usados</h3>
              <Ranking
                items={data.top_parts.map((p) => ({
                  ...p,
                  value: Number(p.quantity ?? 0),
                  display: quantity(p.quantity),
                }))}
                empty="Sin materiales usados en el período."
              />
            </section>
            <section className="card dashboard__card" aria-label="Fallas y reparaciones">
              <h3>Fallas más comunes</h3>
              <Ranking
                items={data.top_failures.map((f) => ({
                  ...f,
                  value: f.count,
                  display: String(f.count),
                }))}
                empty="Sin fallas registradas en el período."
              />
              <h3>Reparaciones más comunes</h3>
              <Ranking
                items={data.top_repairs.map((r) => ({
                  ...r,
                  value: r.count,
                  display: String(r.count),
                }))}
                empty="Sin reparaciones registradas en el período."
              />
              {(data.other_failures.length > 0 || data.other_repairs.length > 0) && (
                <p className="muted">
                  Escritos en «Otro»:{" "}
                  {[...data.other_failures, ...data.other_repairs]
                    .map((o) => `${o.label} (${o.count})`)
                    .join(", ")}
                  . <Link to="/catalogos/listas/escrito-por-escuadrillas">Sumarlos a la lista</Link>
                </p>
              )}
            </section>
            <section className="card dashboard__card" aria-label="Trabajos por técnico">
              <h3>Trabajos por técnico</h3>
              <Ranking
                items={data.by_technician.map((t) => ({
                  ...t,
                  value: t.count,
                  display: String(t.count),
                }))}
                empty="Sin cierres en el período."
              />
              <h3>En curso por escuadrilla</h3>
              <Ranking
                items={data.in_progress_by_crew.map((c) => ({
                  ...c,
                  value: c.count,
                  display: String(c.count),
                }))}
                empty="Ninguna escuadrilla tiene órdenes asignadas."
              />
            </section>
            <section
              className="card dashboard__card dashboard__card--wide"
              aria-label="Mantenimiento"
            >
              <h3>Mantenimiento preventivo</h3>
              <dl className="dashboard__facts">
                {(
                  [
                    ["Generados", data.maintenance.generated],
                    ["Pendientes", data.maintenance.pending],
                    ["Asignados", data.maintenance.assigned],
                    ["Cerrados", data.maintenance.closed],
                    ["Cancelados", data.maintenance.cancelled],
                  ] as const
                ).map(([label, value]) => (
                  <div key={label} className="dashboard__fact">
                    <dt>{label}</dt>
                    <dd>{value}</dd>
                  </div>
                ))}
              </dl>
            </section>
          </div>
        </>
      )}
    </section>
  );
}
