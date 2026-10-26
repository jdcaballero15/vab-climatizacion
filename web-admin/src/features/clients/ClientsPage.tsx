import { useState } from "react";

import { ClientContacts } from "./ClientContacts";
import { ClientForm } from "./ClientForm";
import { EMPTY_CLIENT } from "./formValues";
import { SEGMENT_LABELS } from "./labels";
import type { ClientSegment } from "./types";
import {
  PAGE_SIZE,
  useClient,
  useClientPage,
  useCreateClient,
  useUpdateClient,
} from "./useClients";

function ClientDetail({ clientId, onClose }: { clientId: string; onClose: () => void }) {
  const client = useClient(clientId);
  const updateClient = useUpdateClient(clientId);

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
        <h3>
          Cliente N° {number}: {name}
        </h3>
        <button type="button" onClick={onClose}>
          Cerrar
        </button>
      </header>
      <ClientForm
        // Se rearma con los datos guardados después de cada edición.
        key={`${id}-${name}-${segment}-${tax_id}-${tax_condition}-${notes}`}
        idPrefix={`edit-${id}`}
        title="Editar cliente"
        initial={{ name, segment, tax_id, tax_condition, notes }}
        excludeId={id}
        submitLabel="Guardar cambios"
        isPending={updateClient.isPending}
        error={updateClient.error}
        onSubmit={(values) => updateClient.mutate(values)}
      />
      <ClientContacts clientId={id} />
    </section>
  );
}

export function ClientsPage() {
  const [segment, setSegment] = useState<ClientSegment | null>(null);
  const [offset, setOffset] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const page = useClientPage(segment, offset);
  const createClient = useCreateClient();

  const total = page.data?.total ?? 0;
  const items = page.data?.items ?? [];

  return (
    <section className="clients">
      <h2>Clientes</h2>

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
              setSelectedId(creado.id);
            },
          })
        }
      />

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

      {selectedId && (
        <ClientDetail key={selectedId} clientId={selectedId} onClose={() => setSelectedId(null)} />
      )}
    </section>
  );
}
