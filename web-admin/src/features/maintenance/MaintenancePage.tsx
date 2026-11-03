import { useState } from "react";
import { Link } from "react-router-dom";

import { PageHeader } from "../../app/PageHeader";
import { businessToday, formatDay, ORDER_STATUS_LABELS } from "../orders/labels";
import { everyText, SKIP_REASONS } from "./labels";
import { PlanForm } from "./PlanForm";
import type { MaintenancePlan, MaintenanceRun } from "./types";
import { usePlans, useRunMaintenance, useUpdatePlan } from "./useMaintenance";

/**
 * Planes de mantenimiento por equipo (E07-03). Una semana antes de cada visita el sistema
 * genera la orden sola (E07-04); "Generar ahora" corre lo mismo sin esperar a la mañana.
 */
export function MaintenancePage() {
  const [showEnded, setShowEnded] = useState(false);
  const [creating, setCreating] = useState(false);
  const plans = usePlans(showEnded);
  const run = useRunMaintenance();

  return (
    <section className="catalog">
      <PageHeader
        eyebrow="Abonos"
        title="Mantenimiento preventivo"
        subtitle={
          "Cada equipo abonado tiene su plan: cada cuántos meses se visita y cuándo toca la " +
          "próxima. Una semana antes se genera la orden en Pendientes y se asigna como cualquier otra."
        }
        actions={
          <div className="users__actions">
            <button type="button" onClick={() => run.mutate()} disabled={run.isPending}>
              Generar ahora
            </button>
            <button type="button" onClick={() => setCreating(true)} disabled={creating}>
              Nuevo plan
            </button>
          </div>
        }
      />
      {run.isError && <p role="alert">{run.error.message}</p>}
      {run.data && <RunSummary result={run.data} />}
      {creating && <PlanForm onDone={() => setCreating(false)} />}
      <label className="catalog__toggle">
        <input
          type="checkbox"
          checked={showEnded}
          onChange={(event) => setShowEnded(event.target.checked)}
        />
        Ver también los terminados
      </label>
      {plans.isLoading && <p>Cargando planes…</p>}
      {plans.isError && <p role="alert">No se pudieron cargar los planes.</p>}
      {plans.data?.length === 0 && (
        <p>Todavía no hay planes. Creá uno para que el sistema genere sus visitas.</p>
      )}
      {plans.data && plans.data.length > 0 && (
        <div className="clients__history-scroll">
          <table className="users__table" aria-label="Planes de mantenimiento">
            <thead>
              <tr>
                <th>Cliente y equipo</th>
                <th>Frecuencia</th>
                <th>Próxima visita</th>
                <th>Escuadrilla</th>
                <th>Orden</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {plans.data.map((plan) => (
                <PlanRow key={plan.id} plan={plan} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function RunSummary({ result }: { result: MaintenanceRun }) {
  const count = result.generated.length;
  return (
    <div role="status">
      <p>
        {count === 0
          ? "No había visitas para generar."
          : `${count === 1 ? "Se generó 1 orden" : `Se generaron ${count} órdenes`}: ${result.generated
              .map((item) => `N° ${item.number} (${item.equipment_code})`)
              .join(", ")}.`}
      </p>
      {result.skipped.length > 0 && (
        <ul>
          {result.skipped.map((item) => (
            <li key={item.plan_id}>
              No se generó {item.equipment_code}: {SKIP_REASONS[item.reason] ?? item.reason}.
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function PlanRow({ plan }: { plan: MaintenancePlan }) {
  const [editing, setEditing] = useState(false);
  const [ending, setEnding] = useState(false);
  const update = useUpdatePlan(plan.id);
  const name = plan.equipment.internal_code;

  if (editing) {
    return (
      <tr>
        <td colSpan={6}>
          <PlanForm plan={plan} onDone={() => setEditing(false)} />
        </td>
      </tr>
    );
  }
  return (
    <tr>
      <td>
        <strong>{plan.client.name}</strong>
        <br />
        {name} · {plan.equipment.equipment_type_name} · {plan.equipment.location_note}
      </td>
      <td>{everyText(plan.every_months)}</td>
      <td>
        {plan.active ? formatDay(plan.next_due_on) : "Terminado"}
        {plan.ends_on && plan.active && (
          <>
            <br />
            <span className="muted">Termina el {formatDay(plan.ends_on)}</span>
          </>
        )}
      </td>
      <td>{plan.crew?.name ?? "Sin escuadrilla fija"}</td>
      <td>
        {plan.open_order ? (
          <Link to={`/ordenes/${plan.open_order.id}`}>
            N° {plan.open_order.number} · {ORDER_STATUS_LABELS[plan.open_order.status]}
          </Link>
        ) : (
          "-"
        )}
      </td>
      <td>
        {ending ? (
          <div className="users__actions">
            <span>¿Terminar el plan? No se generan más visitas.</span>
            <button
              type="button"
              disabled={update.isPending}
              onClick={() =>
                update.mutate({ ends_on: businessToday() }, { onSuccess: () => setEnding(false) })
              }
            >
              Terminar
            </button>
            <button type="button" onClick={() => setEnding(false)}>
              No
            </button>
          </div>
        ) : (
          <div className="users__actions">
            <button
              type="button"
              aria-label={`Editar el plan de ${name}`}
              onClick={() => setEditing(true)}
            >
              Editar
            </button>
            {plan.active && (
              <button
                type="button"
                aria-label={`Terminar el plan de ${name}`}
                onClick={() => setEnding(true)}
              >
                Terminar
              </button>
            )}
          </div>
        )}
        {update.isError && <p role="alert">{update.error.message}</p>}
      </td>
    </tr>
  );
}
