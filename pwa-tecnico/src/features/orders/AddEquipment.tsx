import { useState, type FormEvent } from "react";

import { useAddEquipment, useEquipmentTypes, type NewEquipment } from "./useAddEquipment";

type Refrigerant = NonNullable<NewEquipment["refrigerant"]>;
type PowerSupply = NonNullable<NewEquipment["power_supply"]>;

const REFRIGERANTS: { value: Refrigerant; label: string }[] = [
  { value: "R22", label: "R22" },
  { value: "R410A", label: "R410A" },
  { value: "R32", label: "R32" },
  { value: "R407C", label: "R407C" },
  { value: "R404A", label: "R404A" },
  { value: "R134a", label: "R134a" },
  { value: "R290", label: "R290" },
  { value: "other", label: "Otro" },
];

const EMPTY = {
  type: "",
  location: "",
  brand: "",
  model: "",
  frigorias: "",
  refrigerant: "",
  power: "",
};

/**
 * "Agregar equipo" en una orden sin equipo (E05-15). El equipo queda en el domicilio de
 * la orden. Necesita conexión: si falla, lo escrito sigue en pantalla para reintentar.
 */
export function AddEquipment({ orderId }: { orderId: string }) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(EMPTY);
  const [missing, setMissing] = useState<string | null>(null);
  const types = useEquipmentTypes(open);
  const add = useAddEquipment(orderId);

  if (!open) {
    return (
      <button
        type="button"
        className="order-start__secondary add-equipment__open"
        onClick={() => setOpen(true)}
      >
        Agregar equipo
      </button>
    );
  }

  const update = (changes: Partial<typeof EMPTY>) => setDraft({ ...draft, ...changes });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const gaps = [
      draft.type === "" && "el tipo",
      draft.location.trim() === "" && "la ubicación",
    ].filter(Boolean);
    if (gaps.length > 0) {
      setMissing(`Falta ${gaps.join(" y ")}.`);
      return;
    }
    setMissing(null);
    add.mutate({
      equipment_type_id: draft.type,
      location_note: draft.location,
      brand: draft.brand || null,
      model: draft.model || null,
      capacity_frigorias: draft.frigorias ? Number(draft.frigorias) : null,
      refrigerant: (draft.refrigerant || null) as Refrigerant | null,
      power_supply: (draft.power || null) as PowerSupply | null,
    });
  };

  return (
    <form className="add-equipment" aria-label="Agregar equipo" onSubmit={submit} noValidate>
      <h2>Agregar equipo</h2>
      <p className="closure__hint">Queda cargado en el cliente para la próxima vez.</p>

      <label htmlFor="eq-type">Tipo</label>
      <select
        id="eq-type"
        className="closure__select"
        value={draft.type}
        onChange={(event) => update({ type: event.target.value })}
      >
        <option value="">{types.isPending ? "Cargando…" : "Elegí el tipo"}</option>
        {types.data?.map((type) => (
          <option key={type.id} value={type.id}>
            {type.name}
          </option>
        ))}
      </select>
      {types.isError && (
        <p className="closure__field-error" role="alert">
          No se pudieron cargar los tipos. Revisá la conexión.
        </p>
      )}

      <label htmlFor="eq-location">Ubicación</label>
      <input
        id="eq-location"
        className="closure__input"
        value={draft.location}
        onChange={(event) => update({ location: event.target.value })}
        placeholder="Living, cocina, habitación 2"
        maxLength={255}
      />

      <label htmlFor="eq-brand">Marca</label>
      <input
        id="eq-brand"
        className="closure__input"
        value={draft.brand}
        onChange={(event) => update({ brand: event.target.value })}
        maxLength={255}
      />

      <label htmlFor="eq-model">Modelo</label>
      <input
        id="eq-model"
        className="closure__input"
        value={draft.model}
        onChange={(event) => update({ model: event.target.value })}
        maxLength={255}
      />

      <label htmlFor="eq-frigorias">Frigorías</label>
      <input
        id="eq-frigorias"
        className="closure__input"
        type="number"
        inputMode="numeric"
        min={1}
        step={1}
        value={draft.frigorias}
        onChange={(event) => update({ frigorias: event.target.value })}
        placeholder="3000"
      />

      <label htmlFor="eq-refrigerant">Gas</label>
      <select
        id="eq-refrigerant"
        className="closure__select"
        value={draft.refrigerant}
        onChange={(event) => update({ refrigerant: event.target.value })}
      >
        <option value="">Sin dato</option>
        {REFRIGERANTS.map((item) => (
          <option key={item.value} value={item.value}>
            {item.label}
          </option>
        ))}
      </select>

      <label htmlFor="eq-power">Alimentación</label>
      <select
        id="eq-power"
        className="closure__select"
        value={draft.power}
        onChange={(event) => update({ power: event.target.value })}
      >
        <option value="">Sin dato</option>
        <option value="220">220 V (monofásica)</option>
        <option value="380">380 V (trifásica)</option>
      </select>

      {(missing ?? add.error?.message) && (
        <p className="closure__field-error" role="alert">
          {missing ?? add.error?.message}
        </p>
      )}
      <div className="order-start__actions">
        <button type="submit" className="order-start__primary" disabled={add.isPending}>
          {add.isPending ? "Guardando…" : "Guardar equipo"}
        </button>
        <button
          type="button"
          className="order-start__secondary"
          disabled={add.isPending}
          onClick={() => {
            add.reset();
            setMissing(null);
            setDraft(EMPTY);
            setOpen(false);
          }}
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
