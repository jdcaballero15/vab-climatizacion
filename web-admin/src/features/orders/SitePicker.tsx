import { MapPinPlus } from "lucide-react";
import type { UseQueryResult } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { EMPTY_SITE, missingAddress } from "../clients/formValues";
import { siteName } from "../clients/labels";
import { SiteFields } from "../clients/SiteFields";
import type { Site, SiteCreate } from "../clients/types";
import { useCreateSite } from "../clients/useClients";
import { activeSites } from "./formValues";

interface SitePickerProps {
  clientId: string;
  sites: UseQueryResult<Site[]>;
  value: string;
  onChange: (siteId: string) => void;
}

/**
 * Domicilio de la orden entre los activos del cliente. Con uno solo se completa solo; con
 * varios se elige, sin valor por defecto; sin ninguno se agrega acá mismo.
 */
export function SitePicker({ clientId, sites, value, onChange }: SitePickerProps) {
  const active = activeSites(sites.data);

  if (sites.isLoading) {
    return <p>Cargando domicilios…</p>;
  }
  if (sites.isError) {
    return <p role="alert">No se pudieron cargar los domicilios.</p>;
  }
  if (active.length === 0) {
    return <NewSite clientId={clientId} onCreated={onChange} />;
  }
  if (active.length === 1) {
    return <p>Domicilio: {siteName(active[0])}</p>;
  }
  return (
    <div className="clients__form">
      <label htmlFor="order-site">Domicilio</label>
      <select id="order-site" value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">Elegí un domicilio</option>
        {active.map((site) => (
          <option key={site.id} value={site.id}>
            {siteName(site)}
          </option>
        ))}
      </select>
    </div>
  );
}

function NewSite({ clientId, onCreated }: { clientId: string; onCreated: (id: string) => void }) {
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
    createSite.mutate(nuevo, { onSuccess: (site) => onCreated(site.id) });
  }

  return (
    <div className="orders__inline-create">
      <p className="orders__inline-create-note">
        <MapPinPlus size={16} aria-hidden="true" /> El cliente no tiene domicilios activos: se
        agrega uno a esta orden
      </p>
      <form className="clients__form" onSubmit={handleCreate} aria-label="Agregar domicilio">
        <SiteFields idPrefix="order-new-site" values={nuevo} onChange={setNuevo} />
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
    </div>
  );
}
