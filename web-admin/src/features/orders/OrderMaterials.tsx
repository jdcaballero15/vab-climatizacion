import { useState, type FormEvent } from "react";

import { NameTakenError } from "../catalogs/errors";
import { useCreatePart, useParts } from "../parts/useParts";
import { formatDate, formatMoney, formatQuantity, toQuantity } from "./labels";
import type { MaterialLine } from "./types";
import {
  useAddMaterialLine,
  useApproveOrder,
  useOrderMaterials,
  usePromoteMaterialLine,
  useRemoveMaterialLine,
  useUpdateMaterialLine,
} from "./useOrderMaterials";

const QUANTITY_HINT = "Revisá la cantidad: mayor que cero, con hasta tres decimales.";

interface OrderMaterialsProps {
  orderId: string;
  orderNumber: number;
}

/**
 * Materiales de la orden con precio y total (E05-05). Hasta aprobarla, administración
 * corrige, agrega, saca y pasa a la lista los "Otro"; al aprobarla el precio queda fijo.
 */
export function OrderMaterials({ orderId, orderNumber }: OrderMaterialsProps) {
  const materials = useOrderMaterials(orderId);
  const approve = useApproveOrder(orderId);

  if (materials.isLoading) {
    return <p>Cargando materiales…</p>;
  }
  if (materials.isError || !materials.data) {
    return <p role="alert">No se pudieron cargar los materiales.</p>;
  }
  const { approved, approved_at: approvedAt, lines, total } = materials.data;
  const editable = !approved;
  // Los precios arrancan en $0: aprobar con uno así lo deja en $0 para siempre.
  const atZero = lines.filter((line) => line.unit_price !== null && Number(line.unit_price) === 0);

  return (
    <section
      className="order-materials"
      aria-label={`Materiales y aprobación de la orden N° ${orderNumber}`}
    >
      <h4>Materiales</h4>
      {lines.length === 0 ? (
        <p className="muted">La escuadrilla no cargó materiales.</p>
      ) : (
        <div className="order-materials__wrap">
          <table
            className="order-materials__table"
            aria-label={`Materiales de la orden N° ${orderNumber}`}
          >
            <thead>
              <tr>
                <th scope="col">Material</th>
                <th scope="col">Cantidad</th>
                <th scope="col">Precio unit.</th>
                <th scope="col">Subtotal</th>
                {editable && <th scope="col">Acciones</th>}
              </tr>
            </thead>
            <tbody>
              {lines.map((line) => (
                <MaterialRow key={line.id} orderId={orderId} line={line} editable={editable} />
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="order-materials__total">
        Total materiales: <strong>{formatMoney(total)}</strong>
      </p>

      {editable && <AddMaterialForm orderId={orderId} />}

      {approved ? (
        <p className="order-materials__approved" role="status">
          Aprobada el {approvedAt ? formatDate(approvedAt) : "-"}. Los precios quedaron fijos.
        </p>
      ) : (
        <div className="order-materials__approve">
          <p className="muted">
            Al aprobar, cada material queda con el precio de hoy y ya no se puede cambiar.
          </p>
          {atZero.length > 0 && (
            <p className="order-materials__warning">
              Ojo: {atZero.length} {atZero.length === 1 ? "material" : "materiales"} con precio $0:
              si aprobás ahora, queda en $0. Cargá el precio en Materiales y precios antes de
              aprobar.
            </p>
          )}
          <button type="button" disabled={approve.isPending} onClick={() => approve.mutate()}>
            Aprobar orden
          </button>
          {approve.isError && (
            <p className="clients__error" role="alert">
              {approve.error.message}
            </p>
          )}
        </div>
      )}
    </section>
  );
}

function MaterialRow({
  orderId,
  line,
  editable,
}: {
  orderId: string;
  line: MaterialLine;
  editable: boolean;
}) {
  const update = useUpdateMaterialLine(orderId, line.id);
  const remove = useRemoveMaterialLine(orderId, line.id);
  const [quantity, setQuantity] = useState(formatQuantity(line.quantity));
  const [invalid, setInvalid] = useState(false);
  const [promoting, setPromoting] = useState(false);
  const error = update.error ?? remove.error;

  function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = toQuantity(quantity);
    setInvalid(value === null);
    if (value !== null) {
      update.mutate(value);
    }
  }

  return (
    <tr className={line.is_other ? "order-materials__other" : undefined}>
      <th scope="row">
        {line.is_other ? `Otro: ${line.name}` : line.name}
        <span className="order-materials__visit">
          {line.visit_closed_at
            ? `Visita del ${formatDate(line.visit_closed_at)}`
            : `Agregado por ${line.added_by_name}`}
        </span>
        {promoting && (
          <PromoteForm orderId={orderId} line={line} onDone={() => setPromoting(false)} />
        )}
      </th>
      <td>
        {editable ? (
          <form className="order-materials__qty" onSubmit={handleSave}>
            <input
              aria-label={`Cantidad de ${line.name}`}
              inputMode="decimal"
              value={quantity}
              onChange={(event) => setQuantity(event.target.value)}
            />
            {line.unit && <span>{line.unit}</span>}
            <button type="submit" disabled={update.isPending}>
              Guardar
            </button>
          </form>
        ) : (
          <>
            {formatQuantity(line.quantity)} {line.unit}
          </>
        )}
        {invalid && (
          <p className="clients__error" role="alert">
            {QUANTITY_HINT}
          </p>
        )}
      </td>
      <td>{line.unit_price === null ? "Sin precio" : formatMoney(line.unit_price)}</td>
      <td>{line.subtotal === null ? "-" : formatMoney(line.subtotal)}</td>
      {editable && (
        <td>
          <div className="order-materials__actions">
            {line.is_other && !promoting && (
              <button type="button" onClick={() => setPromoting(true)}>
                Pasar a la lista
              </button>
            )}
            <button type="button" disabled={remove.isPending} onClick={() => remove.mutate()}>
              Sacar
            </button>
          </div>
          {error && (
            <p className="clients__error" role="alert">
              {error.message}
            </p>
          )}
        </td>
      )}
    </tr>
  );
}

/** Crea el material con el texto de "Otro" y la línea pasa a ser ese material (E02-07). */
function PromoteForm({
  orderId,
  line,
  onDone,
}: {
  orderId: string;
  line: MaterialLine;
  onDone: () => void;
}) {
  const create = useCreatePart();
  const promote = usePromoteMaterialLine(orderId, line.id);
  const [name, setName] = useState(line.name);
  const [unit, setUnit] = useState("");
  const pending = create.isPending || promote.isPending;
  const error = create.error ?? promote.error;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    create.mutate(
      { name, unit: unit.trim() || "unidad" },
      { onSuccess: (part) => promote.mutate(part.id, { onSuccess: onDone }) },
    );
  }

  return (
    <form
      className="order-materials__promote"
      aria-label={`Pasar ${line.name} a la lista`}
      onSubmit={handleSubmit}
    >
      <label>
        Nombre
        <input value={name} onChange={(event) => setName(event.target.value)} required />
      </label>
      <label>
        Unidad
        <input
          value={unit}
          placeholder="unidad"
          maxLength={20}
          onChange={(event) => setUnit(event.target.value)}
        />
      </label>
      <p className="muted">
        Entra a la lista con precio $0: ponele el precio en Materiales y precios.
      </p>
      <button type="submit" disabled={pending}>
        Agregar a la lista
      </button>
      <button type="button" onClick={onDone}>
        Cancelar
      </button>
      {error && (
        <p className="clients__error" role="alert">
          {error instanceof NameTakenError
            ? "Ya existe un material con ese nombre: agregalo desde la lista."
            : error.message}
        </p>
      )}
    </form>
  );
}

function AddMaterialForm({ orderId }: { orderId: string }) {
  const parts = useParts(false);
  const add = useAddMaterialLine(orderId);
  const [partId, setPartId] = useState("");
  const [quantity, setQuantity] = useState("");
  const [invalid, setInvalid] = useState(false);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = toQuantity(quantity);
    setInvalid(value === null || partId === "");
    if (value !== null && partId !== "") {
      add.mutate(
        { part_id: partId, quantity: value },
        {
          onSuccess: () => {
            setPartId("");
            setQuantity("");
          },
        },
      );
    }
  }

  return (
    <form className="order-materials__add" onSubmit={handleSubmit}>
      <select
        aria-label="Material a agregar"
        value={partId}
        onChange={(event) => setPartId(event.target.value)}
      >
        <option value="">Elegí un material</option>
        {(parts.data ?? []).map((part) => (
          <option key={part.id} value={part.id}>
            {part.name} ({part.unit})
          </option>
        ))}
      </select>
      <input
        aria-label="Cantidad a agregar"
        inputMode="decimal"
        placeholder="Cantidad (ej: 1,5)"
        value={quantity}
        onChange={(event) => setQuantity(event.target.value)}
      />
      <button type="submit" disabled={add.isPending}>
        Agregar material
      </button>
      {invalid && (
        <p className="clients__error" role="alert">
          Elegí el material y revisá la cantidad.
        </p>
      )}
      {add.isError && (
        <p className="clients__error" role="alert">
          {add.error.message}
        </p>
      )}
    </form>
  );
}
