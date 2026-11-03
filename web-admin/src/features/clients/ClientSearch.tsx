import { Search } from "lucide-react";
import { useEffect, useState } from "react";

import { siteName } from "./labels";
import { useSearch } from "./useClients";

// Espera entre teclas antes de buscar, como en el selector de cliente de la orden.
const SEARCH_DELAY_MS = 250;
const MIN_LENGTH = 2;

/**
 * Busca clientes y equipos (E03-06) por nombre, número, dirección, teléfono o código.
 * Tocar un resultado abre la ficha del cliente.
 */
export function ClientSearch({ onOpen }: { onOpen: (clientId: string) => void }) {
  const [text, setText] = useState("");
  const [query, setQuery] = useState("");
  const [includeDeleted, setIncludeDeleted] = useState(false);
  const results = useSearch(query, includeDeleted);
  const searching = query.length >= MIN_LENGTH;

  useEffect(() => {
    const timer = setTimeout(() => setQuery(text.trim()), SEARCH_DELAY_MS);
    return () => clearTimeout(timer);
  }, [text]);

  function open(clientId: string) {
    setText("");
    setQuery("");
    onOpen(clientId);
  }

  const clients = results.data?.clients ?? [];
  const equipment = results.data?.equipment ?? [];

  return (
    <section className="card clients__search" aria-label="Buscar clientes y equipos">
      <div className="clients__search-bar">
        <Search size={16} aria-hidden="true" />
        <input
          type="search"
          aria-label="Buscar"
          placeholder="Buscar por nombre, dirección, teléfono o código de equipo"
          value={text}
          onChange={(event) => setText(event.target.value)}
        />
        <label className="clients__search-deleted">
          <input
            type="checkbox"
            checked={includeDeleted}
            onChange={(event) => setIncludeDeleted(event.target.checked)}
          />
          Incluir bajas
        </label>
      </div>

      {searching && results.isError && <p role="alert">No se pudo buscar.</p>}
      {searching && results.data && clients.length === 0 && equipment.length === 0 && (
        <p className="muted">No se encontró nada con «{query}».</p>
      )}
      {searching && clients.length > 0 && (
        <>
          <h4>Clientes</h4>
          <ul className="clients__search-results" aria-label="Clientes encontrados">
            {clients.map((client) => (
              <li key={client.id}>
                <button type="button" onClick={() => open(client.id)}>
                  <strong>{client.name}</strong>
                  <span>
                    N° {client.number}
                    {client.address && ` · ${client.address}`}
                    {client.deleted && " · Dado de baja"}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
      {searching && equipment.length > 0 && (
        <>
          <h4>Equipos</h4>
          <ul className="clients__search-results" aria-label="Equipos encontrados">
            {equipment.map((item) => (
              <li key={item.id}>
                <button type="button" onClick={() => open(item.client_id)}>
                  <strong>
                    {item.internal_code} · {item.location_note}
                  </strong>
                  <span>
                    {[item.equipment_type_name, item.brand, item.model].filter(Boolean).join(" ")}
                    {" · "}
                    {item.client_name},{" "}
                    {siteName({ label: item.site_label, address: item.site_address })}
                    {item.deleted && " · Dado de baja"}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
