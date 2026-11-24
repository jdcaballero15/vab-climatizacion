import { Plus } from "lucide-react";
import { useState } from "react";

import { ClientContacts } from "./ClientContacts";
import { ClientEquipment } from "./ClientEquipment";
import { ClientHistory } from "./ClientHistory";
import { MonthlyReport } from "./MonthlyReport";
import { ClientLifecycle } from "./ClientLifecycle";
import { ClientSearch } from "./ClientSearch";
import { ClientSites } from "./ClientSites";
import { ClientForm } from "./ClientForm";
import { EMPTY_CLIENT } from "./formValues";
import { SEGMENT_LABELS, TAX_CONDITION_LABELS } from "./labels";
import type { ClientSegment } from "./types";
import {
  PAGE_SIZE,
  useClient,
  useClientPage,
  useContacts,
  useCreateClient,
  useEquipment,
  useSites,
  useUpdateClient,
} from "./useClients";
import { PageHeader } from "../../app/PageHeader";

const TABS = [
  { key: "sites", label: "Domicilios" },
  { key: "equipment", label: "Equipos" },
  { key: "contacts", label: "Contactos" },
  { key: "history", label: "Historial" },
  { key: "report", label: "Informe del mes" },
  { key: "lifecycle", label: "Baja y unificación" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

/** Cuántos hay de cada cosa, para la pestaña; null mientras carga. */
function useTabCounts(clientId: string): Partial<Record<TabKey, number>> {
  const sites = useSites(clientId).data;
  const equipment = useEquipment(clientId, null).data;
  const contacts = useContacts(clientId).data;
  return {
    sites: sites?.filter((site) => site.is_active).length,
    equipment: equipment?.length,
    contacts: contacts?.length,
  };
}

/** Ficha del cliente: los datos para leer arriba y el resto en pestañas. Los formularios
 * se abren al pedirlos, para que se vea lo cargado y no los campos vacíos. */
function ClientDetail({ clientId, onClose }: { clientId: string; onClose: () => void }) {
  const client = useClient(clientId);
  const updateClient = useUpdateClient(clientId);
  const [editing, setEditing] = useState(false);
  const [tab, setTab] = useState<TabKey>("sites");
  const counts = useTabCounts(clientId);

  if (client.isLoading) {
    return <p>Cargando cliente…</p>;
  }
  if (client.isError || !client.data) {
    return <p role="alert">No se pudo cargar el cliente.</p>;
  }

  const { id, number, name, segment, tax_id, tax_condition, notes } = client.data;
  return (
    <section className="clients__detail" aria-label={`Cliente ${name}`}>
      <header className="clients__detail-header">
        <div>
          <span className="muted">Cliente N° {number}</span>
          <h3>{name}</h3>
        </div>
        {!editing && (
          <button type="button" onClick={() => setEditing(true)}>
            Editar datos
          </button>
        )}
        <button type="button" onClick={onClose}>
          Volver a la lista
        </button>
      </header>
      {editing ? (
        <div className="clients__edit">
          <ClientForm
            idPrefix={`edit-${id}`}
            title="Editar datos del cliente"
            initial={{ name, segment, tax_id, tax_condition, notes }}
            excludeId={id}
            submitLabel="Guardar cambios"
            isPending={updateClient.isPending}
            error={updateClient.error}
            onSubmit={(values) =>
              updateClient.mutate(values, { onSuccess: () => setEditing(false) })
            }
          />
          <button
            type="button"
            onClick={() => {
              updateClient.reset();
              setEditing(false);
            }}
          >
            Cancelar
          </button>
        </div>
      ) : (
        <dl className="clients__summary" aria-label="Datos del cliente">
          <div>
            <dt>Segmento</dt>
            <dd>{SEGMENT_LABELS[segment]}</dd>
          </div>
          <div>
            <dt>CUIT o DNI</dt>
            <dd>{tax_id || "Sin dato"}</dd>
          </div>
          <div>
            <dt>Condición fiscal</dt>
            <dd>{tax_condition ? TAX_CONDITION_LABELS[tax_condition] : "Sin dato"}</dd>
          </div>
          {notes && (
            <div className="clients__summary-wide">
              <dt>Observaciones</dt>
              <dd>{notes}</dd>
            </div>
          )}
        </dl>
      )}

      <div className="tabs" role="tablist" aria-label="Secciones del cliente">
        {TABS.map((item) => (
          <button
            key={item.key}
            type="button"
            role="tab"
            id={`client-tab-${item.key}`}
            aria-selected={tab === item.key}
            aria-controls="client-tab-panel"
            className={`tabs__tab${tab === item.key ? " active" : ""}`}
            onClick={() => setTab(item.key)}
          >
            {item.label}
            {counts[item.key] !== undefined && (
              <span className="tabs__total">{counts[item.key]}</span>
            )}
          </button>
        ))}
      </div>
      <div id="client-tab-panel" role="tabpanel" aria-labelledby={`client-tab-${tab}`}>
        {tab === "sites" && <ClientSites clientId={id} />}
        {tab === "equipment" && <ClientEquipment clientId={id} />}
        {tab === "contacts" && <ClientContacts clientId={id} />}
        {tab === "history" && <ClientHistory clientId={id} />}
        {tab === "report" && <MonthlyReport clientId={id} />}
        {tab === "lifecycle" && <ClientLifecycle client={client.data} />}
      </div>
    </section>
  );
}

export function ClientsPage() {
  const [segment, setSegment] = useState<ClientSegment | null>(null);
  const [offset, setOffset] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  // Los dados de baja se listan aparte, para restaurarlos (E03-07).
  const [showDeleted, setShowDeleted] = useState(false);
  const page = useClientPage(segment, offset, showDeleted);
  const createClient = useCreateClient();

  const total = page.data?.total ?? 0;
  const items = page.data?.items ?? [];

  return (
    <section className="clients">
      <PageHeader
        eyebrow="Operación"
        title="Clientes"
        subtitle="Clientes con sus domicilios, contactos y equipos."
        actions={
          <button
            type="button"
            className={creating ? undefined : "btn--primary"}
            aria-expanded={creating}
            onClick={() => setCreating((open) => !open)}
          >
            {creating ? (
              "Cerrar"
            ) : (
              <>
                <Plus size={16} aria-hidden="true" />
                Nuevo cliente
              </>
            )}
          </button>
        }
      />

      {creating && (
        <div className="card form-card">
          <ClientForm
            idPrefix="new-client"
            title="Nuevo cliente"
            initial={EMPTY_CLIENT}
            submitLabel="Crear cliente"
            isPending={createClient.isPending}
            error={createClient.error}
            onSubmit={(values, reset) =>
              createClient.mutate(values, {
                onSuccess: (creado) => {
                  reset();
                  setCreating(false);
                  setSelectedId(creado.id);
                },
              })
            }
          />
        </div>
      )}

      {selectedId ? (
        <ClientDetail key={selectedId} clientId={selectedId} onClose={() => setSelectedId(null)} />
      ) : (
        <>
          <ClientSearch onOpen={setSelectedId} />

          <div className="clients__filters">
            <label htmlFor="segment-filter">Filtrar por segmento</label>
            <select
              id="segment-filter"
              value={segment ?? ""}
              onChange={(event) => {
                setSegment((event.target.value || null) as ClientSegment | null);
                setOffset(0);
              }}
            >
              <option value="">Todos</option>
              {Object.entries(SEGMENT_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <label>
              <input
                type="checkbox"
                checked={showDeleted}
                onChange={(event) => {
                  setShowDeleted(event.target.checked);
                  setOffset(0);
                }}
              />{" "}
              Ver dados de baja
            </label>
          </div>

          {page.isLoading && <p>Cargando clientes…</p>}
          {page.isError && <p role="alert">No se pudieron cargar los clientes.</p>}

          {page.data && items.length === 0 && <p>No hay clientes para mostrar.</p>}
          {items.length > 0 && (
            <>
              <table className="users__table">
                <thead>
                  <tr>
                    <th>Número</th>
                    <th>Nombre</th>
                    <th>Segmento</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {items.map((client) => (
                    <tr key={client.id}>
                      <td>{client.number}</td>
                      <td>{client.name}</td>
                      <td>{SEGMENT_LABELS[client.segment]}</td>
                      <td>
                        <button
                          type="button"
                          aria-label={`Ver ${client.name}`}
                          onClick={() => setSelectedId(client.id)}
                        >
                          Ver
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <nav className="clients__pager" aria-label="Páginas de clientes">
                <button
                  type="button"
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                  disabled={offset === 0}
                >
                  Anterior
                </button>
                <span>
                  {offset + 1} a {offset + items.length} de {total}
                </span>
                <button
                  type="button"
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                  disabled={offset + PAGE_SIZE >= total}
                >
                  Siguiente
                </button>
              </nav>
            </>
          )}
        </>
      )}
    </section>
  );
}
