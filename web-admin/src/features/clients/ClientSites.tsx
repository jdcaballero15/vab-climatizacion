import { useState, type FormEvent } from "react";

import { equipmentCountLabel, siteName } from "./labels";
import type { Site, SiteCreate } from "./types";
import { useCreateSite, useSites, useUpdateSite } from "./useClients";

const EMPTY_SITE: SiteCreate = { label: null, address: "", reference: null };

interface SiteFieldsProps {
  idPrefix: string;
  values: SiteCreate;
  onChange: (values: SiteCreate) => void;
}

function SiteFields({ idPrefix, values, onChange }: SiteFieldsProps) {
  const id = (field: string) => `${idPrefix}-${field}`;
  return (
    <>
      <label htmlFor={id("label")}>Etiqueta</label>
      <input
        id={id("label")}
        value={values.label ?? ""}
        onChange={(event) => onChange({ ...values, label: event.target.value || null })}
        placeholder="Sede central, depósito"
        maxLength={255}
      />
      <label htmlFor={id("address")}>Dirección</label>
      <input
        id={id("address")}
        value={values.address}
        onChange={(event) => onChange({ ...values, address: event.target.value })}
        placeholder="Calle y número, localidad"
        maxLength={255}
      />
      <label htmlFor={id("reference")}>Referencia</label>
      <input
        id={id("reference")}
        value={values.reference ?? ""}
        onChange={(event) => onChange({ ...values, reference: event.target.value || null })}
        placeholder="Piso, departamento, cómo llegar"
        maxLength={500}
      />
    </>
  );
}

// El backend también la rechaza; acá se evita el viaje y se avisa en el formulario.
function missingAddress(values: SiteCreate): boolean {
  return values.address.trim() === "";
}

// Solo los campos editables: el backend rechaza campos de más (id, client_id, map_url).
function editable({ label, address, reference }: Site): SiteCreate {
  return { label, address, reference };
}

function SiteRow({ clientId, site }: { clientId: string; site: Site }) {
  const updateSite = useUpdateSite(clientId, site.id);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<SiteCreate>(() => editable(site));
  const [invalid, setInvalid] = useState(false);
  const name = siteName(site);

  function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (missingAddress(draft)) {
      setInvalid(true);
      return;
    }
    setInvalid(false);
    updateSite.mutate(draft, { onSuccess: () => setEditing(false) });
  }

  if (editing) {
    return (
      <li aria-label={name}>
        <form className="clients__form" onSubmit={handleSave} aria-label={`Editar ${name}`}>
          <SiteFields idPrefix={`site-${site.id}`} values={draft} onChange={setDraft} />
          {invalid && (
            <p className="clients__error" role="alert">
              La dirección es obligatoria.
            </p>
          )}
          {updateSite.isError && (
            <p className="clients__error" role="alert">
              {updateSite.error.message}
            </p>
          )}
          <button type="submit" disabled={updateSite.isPending}>
            Guardar
          </button>
          <button
            type="button"
            onClick={() => {
              updateSite.reset();
              setInvalid(false);
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
    <li className="clients__contact" aria-label={name}>
      {site.label && <strong>{site.label}</strong>}
      <span>{site.address}</span>
      {site.reference && <span>{site.reference}</span>}
      <span>{equipmentCountLabel(site.equipment_count)}</span>
      <a href={site.map_url} target="_blank" rel="noreferrer">
        Ver en el mapa
      </a>
      {!site.is_active && <span className="catalog__badge">Inactivo</span>}
      <button
        type="button"
        aria-label={`Editar ${name}`}
        onClick={() => {
          setDraft(editable(site));
          setEditing(true);
        }}
      >
        Editar
      </button>
      <button
        type="button"
        aria-label={`${site.is_active ? "Desactivar" : "Reactivar"} ${name}`}
        disabled={updateSite.isPending}
        onClick={() => updateSite.mutate({ is_active: !site.is_active })}
      >
        {site.is_active ? "Desactivar" : "Reactivar"}
      </button>
      {updateSite.isError && (
        <span className="clients__error" role="alert">
          {updateSite.error.message}
        </span>
      )}
    </li>
  );
}

/** Domicilios o sedes de un cliente. No se borran: se desactivan. */
export function ClientSites({ clientId }: { clientId: string }) {
  const sites = useSites(clientId);
  const createSite = useCreateSite(clientId);
  const [nuevo, setNuevo] = useState<SiteCreate>(EMPTY_SITE);
  const [invalid, setInvalid] = useState(false);

  function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (missingAddress(nuevo)) {
      setInvalid(true);
      return;
    }
    setInvalid(false);
    createSite.mutate(nuevo, { onSuccess: () => setNuevo(EMPTY_SITE) });
  }

  return (
    <section className="clients__contacts" aria-label="Domicilios">
      <h4>Domicilios</h4>

      {sites.isLoading && <p>Cargando domicilios…</p>}
      {sites.isError && <p role="alert">No se pudieron cargar los domicilios.</p>}
      {sites.data?.length === 0 && <p>Este cliente no tiene domicilios cargados.</p>}
      {sites.data && sites.data.length > 0 && (
        <ul className="clients__contact-list">
          {sites.data.map((site) => (
            <SiteRow key={site.id} clientId={clientId} site={site} />
          ))}
        </ul>
      )}

      <form className="clients__form" onSubmit={handleCreate} aria-label="Agregar domicilio">
        <SiteFields idPrefix={`new-site-${clientId}`} values={nuevo} onChange={setNuevo} />
        {invalid && (
          <p className="clients__error" role="alert">
            La dirección es obligatoria.
          </p>
        )}
        {createSite.isError && (
          <p className="clients__error" role="alert">
            {createSite.error.message}
          </p>
        )}
        <button type="submit" disabled={createSite.isPending}>
          Agregar domicilio
        </button>
      </form>
    </section>
  );
}
