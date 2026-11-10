import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { PageHeader } from "../../app/PageHeader";
import { useCrews } from "../crews/useCrews";
import { formatDateTime } from "../orders/labels";
import { useParts } from "../parts/useParts";
import type { MovementKind, StockLocation } from "./types";
import { useLocations, useMovement, useMovements, useSaveLocation, useStock } from "./useStock";

const KIND_LABELS: Record<MovementKind, string> = {
  receipt: "Ingreso",
  transfer: "Transferencia",
  usage: "Uso en orden",
  adjustment: "Ajuste",
};

type FormKind = "receipt" | "transfer" | "adjustment";

const FORM_TITLES: Record<FormKind, string> = {
  receipt: "Registrar ingreso",
  transfer: "Transferir",
  adjustment: "Ajustar con motivo",
};

/** Cantidad con coma o punto, hasta tres decimales; con signo solo en los ajustes. */
function toQuantity(text: string, signed: boolean): string | null {
  const clean = text.trim().replace(",", ".");
  const pattern = signed ? /^-?\d+(\.\d{1,3})?$/ : /^\d+(\.\d{1,3})?$/;
  return pattern.test(clean) ? clean : null;
}

function quantityText(quantity: string): string {
  return Number(quantity).toLocaleString("es-AR", { maximumFractionDigits: 3 });
}

/**
 * Stock por movimientos (E08): depósitos y camionetas, ingresos, transferencias y ajustes,
 * el stock de cada repuesto por ubicación y su historial. Los saldos negativos (usos sin
 * stock, E08-08) se destacan para ajustarlos. Dirección lo ve sin poder moverlo.
 */
export function StockPage({ readOnly = false }: { readOnly?: boolean }) {
  const [partId, setPartId] = useState("");
  const [locationId, setLocationId] = useState("");
  const [form, setForm] = useState<FormKind | null>(null);
  const [historyOf, setHistoryOf] = useState<string | null>(null);
  const locations = useLocations(false);
  const parts = useParts(false);
  const stock = useStock({ partId, locationId });

  return (
    <section className="catalog">
      <PageHeader
        eyebrow="Operación"
        title="Stock"
        subtitle="Repuestos por depósito y camioneta. Lo usado en cada cierre sale de la camioneta de la escuadrilla."
      />

      {!readOnly && <Locations />}

      {!readOnly && (
        <div className="clients__filters" role="group" aria-label="Movimientos">
          {(Object.keys(FORM_TITLES) as FormKind[]).map((kind) => (
            <button
              key={kind}
              type="button"
              className={form === kind ? "btn--primary" : undefined}
              aria-pressed={form === kind}
              onClick={() => setForm(form === kind ? null : kind)}
            >
              {FORM_TITLES[kind]}
            </button>
          ))}
        </div>
      )}
      {form && <MovementForm kind={form} onDone={() => setForm(null)} />}

      <div className="parts__filters">
        <label>
          Repuesto{" "}
          <select value={partId} onChange={(event) => setPartId(event.target.value)}>
            <option value="">Todos</option>
            {parts.data?.map((part) => (
              <option key={part.id} value={part.id}>
                {part.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Ubicación{" "}
          <select value={locationId} onChange={(event) => setLocationId(event.target.value)}>
            <option value="">Todas</option>
            {locations.data?.map((location) => (
              <option key={location.id} value={location.id}>
                {location.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      {stock.isLoading && <p>Cargando stock…</p>}
      {stock.isError && <p role="alert">No se pudo cargar el stock.</p>}
      {stock.data?.length === 0 && <p>No hay stock cargado.</p>}
      {stock.data && stock.data.length > 0 && (
        <div className="parts__table-wrap">
          <table className="parts__table" aria-label="Stock por repuesto">
            <thead>
              <tr>
                <th scope="col">Repuesto</th>
                <th scope="col">Por ubicación</th>
                <th scope="col">Total</th>
                <th scope="col" />
              </tr>
            </thead>
            <tbody>
              {stock.data.map((part) => (
                <tr
                  key={part.part_id}
                  className={part.has_negative ? "stock__negative" : undefined}
                >
                  <td>
                    {part.part_name}
                    {part.has_negative && (
                      <span className="badge badge--danger">Saldo negativo: ajustar</span>
                    )}
                  </td>
                  <td>
                    {part.by_location.map((row) => (
                      <div key={row.location_id}>
                        {row.location_name}: {quantityText(row.quantity)} {part.unit}
                      </div>
                    ))}
                  </td>
                  <td>
                    {quantityText(part.total)} {part.unit}
                  </td>
                  <td>
                    <button
                      type="button"
                      aria-label={`Historial de ${part.part_name}`}
                      onClick={() => setHistoryOf(historyOf === part.part_id ? null : part.part_id)}
                    >
                      Historial
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {historyOf && <History partId={historyOf} />}
    </section>
  );
}

/** Depósitos y camionetas; la camioneta lleva su escuadrilla (E08-01). */
function Locations() {
  const [showInactive, setShowInactive] = useState(false);
  const locations = useLocations(showInactive);
  const crews = useCrews(false);
  const create = useSaveLocation();
  const [name, setName] = useState("");
  const [kind, setKind] = useState<StockLocation["kind"]>("warehouse");
  const [crewId, setCrewId] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) {
      return;
    }
    create.mutate(
      { kind, name: name.trim(), crew_id: kind === "truck" && crewId ? crewId : null },
      {
        onSuccess: () => {
          setName("");
          setCrewId("");
        },
      },
    );
  }

  return (
    <section className="clients__contacts" aria-label="Depósitos y camionetas">
      <h4>Depósitos y camionetas</h4>
      <ul className="clients__contact-list">
        {locations.data?.map((location) => (
          <LocationRow key={location.id} location={location} />
        ))}
      </ul>
      <label className="catalog__toggle">
        <input
          type="checkbox"
          checked={showInactive}
          onChange={(event) => setShowInactive(event.target.checked)}
        />
        Mostrar desactivadas
      </label>
      <form className="clients__form" onSubmit={handleSubmit} aria-label="Nueva ubicación">
        <label>
          Tipo{" "}
          <select
            value={kind}
            onChange={(event) => setKind(event.target.value as StockLocation["kind"])}
          >
            <option value="warehouse">Depósito</option>
            <option value="truck">Camioneta</option>
          </select>
        </label>
        <label>
          Nombre <input value={name} maxLength={255} onChange={(e) => setName(e.target.value)} />
        </label>
        {kind === "truck" && (
          <label>
            Escuadrilla{" "}
            <select value={crewId} onChange={(event) => setCrewId(event.target.value)}>
              <option value="">Sin escuadrilla</option>
              {crews.data?.map((crew) => (
                <option key={crew.id} value={crew.id}>
                  {crew.name}
                </option>
              ))}
            </select>
          </label>
        )}
        {create.isError && (
          <p className="clients__error" role="alert">
            {create.error.message}
          </p>
        )}
        <button type="submit" disabled={create.isPending}>
          Agregar ubicación
        </button>
      </form>
    </section>
  );
}

function LocationRow({ location }: { location: StockLocation }) {
  const save = useSaveLocation(location.id);
  return (
    <li className="clients__contact" aria-label={location.name}>
      <strong>{location.name}</strong>
      <span>{location.kind === "truck" ? "Camioneta" : "Depósito"}</span>
      {location.crew_name && <span>{location.crew_name}</span>}
      {!location.is_active && <span className="muted">Desactivada</span>}
      <button
        type="button"
        disabled={save.isPending}
        onClick={() => save.mutate({ is_active: !location.is_active })}
      >
        {location.is_active ? "Desactivar" : "Activar"}
      </button>
      {save.isError && <span role="alert">{save.error.message}</span>}
    </li>
  );
}

function MovementForm({ kind, onDone }: { kind: FormKind; onDone: () => void }) {
  const locations = useLocations(false);
  const parts = useParts(false);
  const movement = useMovement();
  const [partId, setPartId] = useState("");
  const [fromId, setFromId] = useState("");
  const [toId, setToId] = useState("");
  const [quantity, setQuantity] = useState("");
  const [reason, setReason] = useState("");
  const [invalid, setInvalid] = useState<string | null>(null);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = toQuantity(quantity, kind === "adjustment");
    const location = kind === "transfer" ? fromId : toId;
    if (!partId || !location || (kind === "transfer" && !toId)) {
      setInvalid("Elegí el repuesto y la ubicación.");
      return;
    }
    if (value === null || Number(value) === 0 || (kind !== "adjustment" && Number(value) <= 0)) {
      setInvalid("Revisá la cantidad: un número distinto de cero, con hasta tres decimales.");
      return;
    }
    if (kind === "adjustment" && !reason.trim()) {
      setInvalid("El ajuste necesita un motivo.");
      return;
    }
    setInvalid(null);
    const request =
      kind === "receipt"
        ? { kind, body: { part_id: partId, location_id: toId, quantity: value } }
        : kind === "transfer"
          ? {
              kind,
              body: {
                part_id: partId,
                from_location_id: fromId,
                to_location_id: toId,
                quantity: value,
              },
            }
          : {
              kind,
              body: { part_id: partId, location_id: toId, quantity: value, reason: reason.trim() },
            };
    movement.mutate(request, { onSuccess: onDone });
  }

  const locationSelect = (label: string, value: string, set: (id: string) => void) => (
    <label>
      {label}{" "}
      <select value={value} onChange={(event) => set(event.target.value)}>
        <option value="">Elegí</option>
        {locations.data?.map((location) => (
          <option key={location.id} value={location.id}>
            {location.name}
          </option>
        ))}
      </select>
    </label>
  );

  return (
    <form className="clients__form" onSubmit={handleSubmit} aria-label={FORM_TITLES[kind]}>
      <h4>{FORM_TITLES[kind]}</h4>
      <label>
        Repuesto{" "}
        <select value={partId} onChange={(event) => setPartId(event.target.value)}>
          <option value="">Elegí</option>
          {parts.data?.map((part) => (
            <option key={part.id} value={part.id}>
              {part.name} ({part.unit})
            </option>
          ))}
        </select>
      </label>
      {kind === "transfer" && locationSelect("Desde", fromId, setFromId)}
      {locationSelect(kind === "transfer" ? "Hacia" : "Ubicación", toId, setToId)}
      <label>
        Cantidad{kind === "adjustment" ? " (negativa para restar)" : ""}{" "}
        <input
          inputMode="decimal"
          value={quantity}
          onChange={(event) => setQuantity(event.target.value)}
        />
      </label>
      {kind === "adjustment" && (
        <label>
          Motivo{" "}
          <input
            value={reason}
            maxLength={255}
            onChange={(event) => setReason(event.target.value)}
          />
        </label>
      )}
      {(invalid ?? (movement.isError ? movement.error.message : null)) && (
        <p className="clients__error" role="alert">
          {invalid ?? movement.error?.message}
        </p>
      )}
      <button type="submit" className="btn--primary" disabled={movement.isPending}>
        Guardar
      </button>
      <button type="button" onClick={onDone}>
        Cancelar
      </button>
    </form>
  );
}

/** Todos los movimientos del repuesto, el más nuevo primero (E08-07). */
function History({ partId }: { partId: string }) {
  const movements = useMovements(partId);
  return (
    <section className="clients__contacts" aria-label="Historial del repuesto">
      <h4>Historial</h4>
      {movements.isLoading && <p>Cargando historial…</p>}
      {movements.data?.length === 0 && <p>Sin movimientos.</p>}
      <ul className="clients__contact-list">
        {movements.data?.map((movement) => (
          <li key={movement.id}>
            {formatDateTime(movement.occurred_at)} · {KIND_LABELS[movement.kind]} ·{" "}
            {quantityText(movement.quantity)}
            {movement.from_location_name && ` · desde ${movement.from_location_name}`}
            {movement.to_location_name && ` · hacia ${movement.to_location_name}`}
            {movement.work_order_id && (
              <>
                {" · "}
                <Link to={`/ordenes/${movement.work_order_id}`}>
                  Orden N° {movement.work_order_number}
                </Link>
              </>
            )}
            {movement.reason && ` · ${movement.reason}`} · {movement.created_by_name}
          </li>
        ))}
      </ul>
    </section>
  );
}
