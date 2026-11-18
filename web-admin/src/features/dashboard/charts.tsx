import { useState } from "react";

import type { Dashboard } from "./useDashboard";

type Week = Dashboard["weeks"][number];

// Dos series con orden fijo de la paleta categórica (validada: CVD y contraste vs. blanco).
const SERIES = { created: "#2a78d6", done: "#eb6834" } as const;
const LABELS = { created: "Creadas", done: "Terminadas" } as const;

function weekLabel(day: string): string {
  const [, month, date] = day.split("-");
  return `${date}/${month}`;
}

/** Tope del eje redondeado hacia arriba, para que las tres marcas sean números enteros. */
function axisMax(max: number): number {
  return max <= 2 ? 2 : Math.ceil(max / 2) * 2;
}

/**
 * Evolución por semana: barras agrupadas de creadas y terminadas (E10-01). Leyenda arriba,
 * eje con tres marcas, valor de cada barra al pasar o enfocar, y la misma información como
 * tabla. Las columnas se reparten el ancho de la tarjeta.
 */
export function WeeklyChart({ weeks }: { weeks: Week[] }) {
  const [active, setActive] = useState<{ week: Week; key: keyof typeof LABELS } | null>(null);
  const [asTable, setAsTable] = useState(false);
  const top = axisMax(Math.max(0, ...weeks.flatMap((w) => [w.created, w.done])));
  const ticks = [top, top / 2, 0];
  const columns = { gridTemplateColumns: `repeat(${weeks.length}, minmax(0, 1fr))` };

  return (
    <div className="dashboard__chart">
      <div className="dashboard__legend">
        {(Object.keys(LABELS) as (keyof typeof LABELS)[]).map((key) => (
          <span key={key}>
            <i style={{ background: SERIES[key] }} aria-hidden="true" /> {LABELS[key]}
          </span>
        ))}
        <button type="button" className="btn--ghost btn--sm" onClick={() => setAsTable((t) => !t)}>
          {asTable ? "Ver gráfico" : "Ver tabla"}
        </button>
      </div>
      {asTable ? (
        <table className="parts__table" aria-label="Órdenes por semana">
          <thead>
            <tr>
              <th scope="col">Semana del</th>
              <th scope="col">Creadas</th>
              <th scope="col">Terminadas</th>
            </tr>
          </thead>
          <tbody>
            {weeks.map((week) => (
              <tr key={week.week_start}>
                <td>{weekLabel(week.week_start)}</td>
                <td>{week.created}</td>
                <td>{week.done}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="weekly" role="img" aria-label="Órdenes creadas y terminadas por semana">
          <div className="weekly__axis" aria-hidden="true">
            {ticks.map((tick) => (
              <span key={tick}>{tick}</span>
            ))}
          </div>
          <div className="weekly__plot">
            {ticks.map((tick) => (
              <span
                key={tick}
                className="weekly__grid"
                style={{ bottom: `${(tick / top) * 100}%` }}
                aria-hidden="true"
              />
            ))}
            <div className="weekly__columns" style={columns}>
              {weeks.map((week) => (
                <div key={week.week_start} className="weekly__week">
                  {(["created", "done"] as const).map((key) => (
                    <span
                      key={key}
                      className="weekly__bar"
                      style={{
                        height: `${(week[key] / top) * 100}%`,
                        background: SERIES[key],
                      }}
                      tabIndex={0}
                      aria-label={`${LABELS[key]} la semana del ${weekLabel(week.week_start)}: ${week[key]}`}
                      onPointerEnter={() => setActive({ week, key })}
                      onFocus={() => setActive({ week, key })}
                      onPointerLeave={() => setActive(null)}
                      onBlur={() => setActive(null)}
                    />
                  ))}
                </div>
              ))}
            </div>
          </div>
          <div className="weekly__ticks" style={columns} aria-hidden="true">
            {weeks.map((week) => (
              <span key={week.week_start}>{weekLabel(week.week_start)}</span>
            ))}
          </div>
        </div>
      )}
      <p className="dashboard__readout" aria-live="polite">
        {active
          ? `Semana del ${weekLabel(active.week.week_start)}: ${active.week.created} creadas, ${active.week.done} terminadas`
          : " "}
      </p>
    </div>
  );
}

/** Ranking horizontal de una sola serie: nombre completo y valor arriba, la barra abajo. */
export function Ranking({
  items,
  empty,
  unit,
}: {
  items: { key: string; label: string; value: number; display: string }[];
  empty: string;
  unit?: string;
}) {
  if (items.length === 0) {
    return <p className="muted">{empty}</p>;
  }
  const max = Math.max(...items.map((item) => item.value), 1);
  return (
    <ol className="dashboard__ranking">
      {items.map((item) => (
        <li key={item.key}>
          <span className="dashboard__ranking-label">{item.label}</span>
          <span className="dashboard__ranking-value">
            {item.display}
            {unit ?? ""}
          </span>
          <span className="dashboard__ranking-track" aria-hidden="true">
            <span
              className="dashboard__ranking-bar"
              style={{ width: `${(item.value / max) * 100}%`, background: SERIES.created }}
            />
          </span>
        </li>
      ))}
    </ol>
  );
}
