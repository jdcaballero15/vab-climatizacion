import { useState, type FormEvent } from "react";

import { PageHeader } from "../../app/PageHeader";
import { NameTakenError } from "../catalogs/errors";
import { formatDateTime, toAmount } from "../orders/labels";
import { findSimilar, matchesSearch } from "./similar";
import type { Part } from "./types";
import { useCreatePart, useParts, useSetPartPrice, useUpdatePart } from "./useParts";

const UNIT_SUGGESTIONS = ["unidad", "kg", "metro", "litro"];
const NAME_TAKEN = "Ya existe un material con ese nombre (puede estar desactivado).";

/**
 * Lista de materiales que eligen las escuadrillas y su precio de lista (E02-05, E02-06).
 * Cada precio nuevo queda guardado con fecha; las órdenes aprobadas conservan el suyo.
 */
export function PartsPage() {
  const [showInactive, setShowInactive] = useState(false);
  const [search, setSearch] = useState("");
  const parts = useParts(showInactive);
  const visible = (parts.data ?? []).filter((part) => matchesSearch(part.name, search));

  return (
    <section className="catalog">
      <PageHeader
        eyebrow="Catálogos"
        title="Materiales y precios"
        subtitle="Los materiales que eligen las escuadrillas al cerrar. Los precios los ve solo administración."
      />

      <NewPartForm existing={parts.data ?? []} />

      <div className="parts__filters">
        <input
          aria-label="Buscar material"
          placeholder="Buscar material"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <label className="catalog__toggle">
          <input
            type="checkbox"
            checked={showInactive}
            onChange={(event) => setShowInactive(event.target.checked)}
          />
          Mostrar desactivados
        </label>
      </div>

      {parts.isLoading && <p>Cargando materiales…</p>}
      {parts.isError && <p role="alert">No se pudieron cargar los materiales.</p>}
      {parts.data && visible.length === 0 && <p>No hay materiales para mostrar.</p>}
      {visible.length > 0 && (
        <div className="parts__table-wrap">
          <table className="parts__table">
            <thead>
              <tr>
                <th scope="col">Material</th>
                <th scope="col">Unidad</th>
                <th scope="col">Precio ($)</th>
                <th scope="col">Estado</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((part) => (
                <PartRow key={part.id} part={part} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function NewPartForm({ existing }: { existing: Part[] }) {
  const create = useCreatePart();
  const [name, setName] = useState("");
  const [unit, setUnit] = useState("");
  const similar = findSimilar(name, existing);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    create.mutate(
      { name, unit: unit.trim() || "unidad" },
      {
        onSuccess: () => {
          setName("");
          setUnit("");
        },
      },
    );
  }

  return (
    <form className="catalog__new parts__new" onSubmit={handleSubmit}>
      <input
        aria-label="Nuevo material"
        placeholder="Nuevo material"
        value={name}
        onChange={(event) => setName(event.target.value)}
        required
      />
      <input
        aria-label="Unidad"
        placeholder="unidad"
        list="part-units"
        value={unit}
        maxLength={20}
        onChange={(event) => setUnit(event.target.value)}
      />
      <datalist id="part-units">
        {UNIT_SUGGESTIONS.map((suggestion) => (
          <option key={suggestion} value={suggestion} />
        ))}
      </datalist>
      <button type="submit" disabled={create.isPending}>
        Agregar material
      </button>
      {similar && (
        <p className="muted parts__similar">
          Ya hay uno parecido: {similar.name}. Si es otro material, guardalo igual.
        </p>
      )}
      {create.error && (
        <p className="catalog__error" role="alert">
          {create.error instanceof NameTakenError ? NAME_TAKEN : "No se pudo guardar."}
        </p>
      )}
    </form>
  );
}

function PartRow({ part }: { part: Part }) {
  const update = useUpdatePart(part.id);
  const setPrice = useSetPartPrice(part.id);
  const [price, setPriceText] = useState(part.list_price.replace(".", ","));
  const [invalid, setInvalid] = useState(false);

  function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const amount = toAmount(price);
    setInvalid(amount === null);
    if (amount !== null) {
      setPrice.mutate(amount);
    }
  }

  return (
    <tr className={part.is_active ? undefined : "catalog__inactive"}>
      <th scope="row">{part.name}</th>
      <td>{part.unit}</td>
      <td>
        <form className="parts__price" onSubmit={handleSave}>
          <input
            aria-label={`Precio de ${part.name}`}
            inputMode="decimal"
            value={price}
            onChange={(event) => setPriceText(event.target.value)}
          />
          <button type="submit" disabled={setPrice.isPending}>
            Guardar precio
          </button>
        </form>
        {invalid && (
          <p className="catalog__error" role="alert">
            Revisá el precio: solo números, con hasta dos decimales.
          </p>
        )}
        {setPrice.isSuccess && !invalid && <p role="status">Precio guardado.</p>}
        {setPrice.isError && (
          <p className="catalog__error" role="alert">
            No se pudo guardar el precio.
          </p>
        )}
        <p className="muted">Actualizado: {formatDateTime(part.price_updated_at)}</p>
      </td>
      <td>
        <button
          type="button"
          disabled={update.isPending}
          onClick={() => update.mutate({ is_active: !part.is_active })}
        >
          {part.is_active ? "Desactivar" : "Reactivar"}
        </button>
      </td>
    </tr>
  );
}
