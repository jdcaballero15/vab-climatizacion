import { useDashboard } from "../dashboard/useDashboard";
import { businessToday } from "../orders/labels";

const MONTH_NAME = new Intl.DateTimeFormat("es-AR", { month: "long", timeZone: "UTC" });

/** Primer y último día del mes de hoy (aaaa-mm-dd), en la hora del negocio. */
function currentMonth(): { from: string; to: string; name: string } {
  const [year, month] = businessToday().split("-").map(Number);
  const last = new Date(Date.UTC(year, month, 0));
  return {
    from: `${year}-${String(month).padStart(2, "0")}-01`,
    to: last.toISOString().slice(0, 10),
    name: MONTH_NAME.format(last),
  };
}

/** Cómo van las visitas de mantenimiento del mes (E10-04): las mismas cuentas que el tablero. */
export function MonthProgress() {
  const month = currentMonth();
  const dashboard = useDashboard({ date_from: month.from, date_to: month.to });
  const progress = dashboard.data?.maintenance;
  if (!progress) {
    return null;
  }
  const facts = [
    ["Generadas", progress.generated],
    ["Sin asignar", progress.pending],
    ["Asignadas", progress.assigned],
    ["Cerradas", progress.closed],
    ["Canceladas", progress.cancelled],
  ] as const;

  return (
    <section className="card dashboard__card maintenance__month" aria-label="Visitas del mes">
      <h3>Visitas de {month.name}</h3>
      <dl className="dashboard__facts">
        {facts.map(([label, value]) => (
          <div key={label} className="dashboard__fact">
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
