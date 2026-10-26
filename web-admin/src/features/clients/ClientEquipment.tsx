import { useState, type FormEvent } from "react";

import { useEquipmentTypes } from "../equipment-types/useEquipmentTypes";
import type { EquipmentType } from "../equipment-types/types";
import { siteName } from "./labels";
import type { Equipment, EquipmentCreate, Site } from "./types";
import { useCreateEquipment, useEquipment, useSites, useUpdateEquipment } from "./useClients";

const EMPTY_EQUIPMENT: EquipmentCreate = {
  client_site_id: "",
  equipment_type_id: "",
  location_note: "",
  brand: null,
  model: null,
  serial_number: null,
  notes: null,
};

interface Choices {
  sites: Site[];
  types: EquipmentType[];
}

interface EquipmentFieldsProps {
  idPrefix: string;
  values: EquipmentCreate;
  choices: Choices;
  onChange: (values: EquipmentCreate) => void;
}

// Se ofrecen los activos; uno inactivo solo aparece si el equipo ya está ahí.
function offered<T extends { id: string; is_active: boolean }>(items: T[], current: string) {
  return items.filter((item) => item.is_active || item.id === current);
}

function EquipmentFields({ idPrefix, values, choices, onChange }: EquipmentFieldsProps) {
  const id = (field: string) => `${idPrefix}-${field}`;
  const optional = (field: "brand" | "model" | "serial_number" | "notes", value: string) =>
    onChange({ ...values, [field]: value || null });
  return (
    <>
      <label htmlFor={id("site")}>Domicilio</label>
      <select
        id={id("site")}
        value={values.client_site_id}
        onChange={(event) => onChange({ ...values, client_site_id: event.target.value })}
      >
        {offered(choices.sites, values.client_site_id).map((site) => (
          <option key={site.id} value={site.id}>
            {siteName(site)}
          </option>
        ))}
      </select>
      <label htmlFor={id("type")}>Tipo de equipo</label>
      <select
        id={id("type")}
        value={values.equipment_type_id}
        onChange={(event) => onChange({ ...values, equipment_type_id: event.target.value })}
      >
        <option value="">Elegí un tipo</option>
        {offered(choices.types, values.equipment_type_id).map((type) => (
          <option key={type.id} value={type.id}>
            {type.name}
          </option>
        ))}
      </select>
      <label htmlFor={id("location")}>Ubicación</label>
      <input
        id={id("location")}
        value={values.location_note}
        onChange={(event) => onChange({ ...values, location_note: event.target.value })}
        placeholder="Habitación 12, oficina planta alta"
        maxLength={255}
      />
      <label htmlFor={id("brand")}>Marca</label>
      <input
        id={id("brand")}
        value={values.brand ?? ""}
        onChange={(event) => optional("brand", event.target.value)}
        maxLength={255}
      />
      <label htmlFor={id("model")}>Modelo</label>
      <input
        id={id("model")}
        value={values.model ?? ""}
        onChange={(event) => optional("model", event.target.value)}
        maxLength={255}
      />
      <label htmlFor={id("serial")}>Número de serie</label>
      <input
        id={id("serial")}
        value={values.serial_number ?? ""}
        onChange={(event) => optional("serial_number", event.target.value)}
        maxLength={255}
      />
      <label htmlFor={id("notes")}>Observaciones</label>
      <textarea
        id={id("notes")}
        value={values.notes ?? ""}
        onChange={(event) => optional("notes", event.target.value)}
        placeholder="Potencia, subtipo, gas refrigerante"
        maxLength={2000}
      />
    </>
  );
}

/** Lo obligatorio que falta, en una frase; null si está completo. El backend también lo valida. */
function missingFields(values: EquipmentCreate): string | null {
  const missing = [
    !values.client_site_id && "el domicilio",
    !values.equipment_type_id && "el tipo de equipo",
    values.location_note.trim() === "" && "la ubicación",
  ].filter((item): item is string => Boolean(item));
  if (missing.length === 0) {
    return null;
  }
  const last = missing.pop();
  return `Falta ${missing.length ? `${missing.join(", ")} y ${last}` : last}.`;
}

// Solo los campos editables: el backend rechaza el código y el id.
function editable(equipment: Equipment): EquipmentCreate {
  const { client_site_id, equipment_type_id, location_note, brand, model, serial_number, notes } =
    equipment;
  return { client_site_id, equipment_type_id, location_note, brand, model, serial_number, notes };
}

interface EquipmentRowProps {
  clientId: string;
  equipment: Equipment;
  choices: Choices;
}

function EquipmentRow({ clientId, equipment, choices }: EquipmentRowProps) {
  const updateEquipment = useUpdateEquipment(clientId, equipment.id);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<EquipmentCreate>(() => editable(equipment));
  const [missing, setMissing] = useState<string | null>(null);
  const code = equipment.internal_code;
  const site = choices.sites.find((item) => item.id === equipment.client_site_id);
  const type = choices.types.find((item) => item.id === equipment.equipment_type_id);

  function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const problem = missingFields(draft);
    setMissing(problem);
    if (problem) {
      return;
    }
    updateEquipment.mutate(draft, { onSuccess: () => setEditing(false) });
  }

  if (editing) {
    return (
      <li aria-label={code}>
        <form className="clients__form" onSubmit={handleSave} aria-label={`Editar ${code}`}>
          <EquipmentFields
            idPrefix={`equipment-${equipment.id}`}
            values={draft}
            choices={choices}
            onChange={setDraft}
          />
          {missing && (
            <p className="clients__error" role="alert">
              {missing}
            </p>
          )}
          {updateEquipment.isError && (
            <p className="clients__error" role="alert">
              {updateEquipment.error.message}
            </p>
          )}
          <button type="submit" disabled={updateEquipment.isPending}>
            Guardar
          </button>
          <button
            type="button"
            onClick={() => {
              updateEquipment.reset();
              setMissing(null);
              setEditing(false);
            }}
          >
            Cancelar
          </button>
        </form>
      </li>
    );
  }

  return (
    <li className="clients__contact" aria-label={code}>
      <strong>{equipment.location_note}</strong>
      {type && <span>{type.name}</span>}
      <span className="catalog__badge">{code}</span>
      {site && <span>{siteName(site)}</span>}
      {equipment.brand && <span>{equipment.brand}</span>}
      {equipment.model && <span>{equipment.model}</span>}
      <button
        type="button"
        aria-label={`Editar ${code}`}
        onClick={() => {
          setDraft(editable(equipment));
          setEditing(true);
        }}
      >
        Editar
      </button>
    </li>
  );
}

/** Equipos de un cliente. El código lo genera el sistema; no se borran (baja en E03-07). */
export function ClientEquipment({ clientId }: { clientId: string }) {
  const [siteFilter, setSiteFilter] = useState<string | null>(null);
  const equipment = useEquipment(clientId, siteFilter);
  const sites = useSites(clientId).data ?? [];
  // Con los inactivos, para mostrar el tipo de un equipo viejo; el formulario los filtra.
  const types = useEquipmentTypes(true).data ?? [];
  const choices = { sites, types };
  const createEquipment = useCreateEquipment(clientId);
  const [nuevo, setNuevo] = useState<EquipmentCreate>(EMPTY_EQUIPMENT);
  const [missing, setMissing] = useState<string | null>(null);
  // Sin elección, el alta va al primer domicilio activo.
  const values = {
    ...nuevo,
    client_site_id: nuevo.client_site_id || (sites.find((site) => site.is_active)?.id ?? ""),
  };

  function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const problem = missingFields(values);
    setMissing(problem);
    if (problem) {
      return;
    }
    createEquipment.mutate(values, { onSuccess: () => setNuevo(EMPTY_EQUIPMENT) });
  }

  return (
    <section className="clients__contacts" aria-label="Equipos">
      <h4>Equipos</h4>

      <div className="clients__filters">
        <label htmlFor={`equipment-filter-${clientId}`}>Filtrar por domicilio</label>
        <select
          id={`equipment-filter-${clientId}`}
          value={siteFilter ?? ""}
          onChange={(event) => setSiteFilter(event.target.value || null)}
        >
          <option value="">Todos</option>
          {sites.map((site) => (
            <option key={site.id} value={site.id}>
              {siteName(site)}
            </option>
          ))}
        </select>
      </div>

      {equipment.isLoading && <p>Cargando equipos…</p>}
      {equipment.isError && <p role="alert">No se pudieron cargar los equipos.</p>}
      {equipment.data?.length === 0 && <p>No hay equipos cargados.</p>}
      {equipment.data && equipment.data.length > 0 && (
        <ul className="clients__contact-list">
          {equipment.data.map((item) => (
            <EquipmentRow key={item.id} clientId={clientId} equipment={item} choices={choices} />
          ))}
        </ul>
      )}

      <form className="clients__form" onSubmit={handleCreate} aria-label="Agregar equipo">
        {sites.some((site) => site.is_active) ? (
          <EquipmentFields
            idPrefix={`new-equipment-${clientId}`}
            values={values}
            choices={choices}
            onChange={setNuevo}
          />
        ) : (
          <p>Para agregar equipos, el cliente necesita un domicilio activo.</p>
        )}
        {missing && (
          <p className="clients__error" role="alert">
            {missing}
          </p>
        )}
        {createEquipment.isError && (
          <p className="clients__error" role="alert">
            {createEquipment.error.message}
          </p>
        )}
        <button type="submit" disabled={createEquipment.isPending}>
          Agregar equipo
        </button>
      </form>
    </section>
  );
}
