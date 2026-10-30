import { useEffect, useState, type FocusEvent } from "react";

import { ClientForm } from "../clients/ClientForm";
import { EMPTY_CLIENT } from "../clients/formValues";
import type { ClientSummary } from "../clients/types";
import { useCreateClient } from "../clients/useClients";
import { useClientOptions } from "./useOrders";

// Espera entre teclas antes de pedir la lista filtrada.
const SEARCH_DELAY_MS = 250;

interface ClientPickerProps {
  selected: ClientSummary | null;
  onSelect: (client: ClientSummary | null) => void;
}

/**
 * Lista desplegable de clientes que se filtra mientras se escribe (nombre o número). Si el
 * cliente no existe, se crea ahí mismo y queda elegido.
 */
export function ClientPicker({ selected, onSelect }: ClientPickerProps) {
  const [text, setText] = useState("");
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const options = useClientOptions(search, open);
  const createClient = useCreateClient();

  useEffect(() => {
    const timer = setTimeout(() => setSearch(text), SEARCH_DELAY_MS);
    return () => clearTimeout(timer);
  }, [text]);

  function choose(client: ClientSummary) {
    // Al volver a buscar (otro cliente u otra orden) se arranca de cero.
    setText("");
    setSearch("");
    setOpen(false);
    setCreating(false);
    onSelect(client);
  }

  function closeWhenFocusLeaves(event: FocusEvent<HTMLDivElement>) {
    if (!event.currentTarget.contains(event.relatedTarget)) {
      setOpen(false);
    }
  }

  if (selected) {
    return (
      <div className="orders__client">
        <span>
          Cliente: <strong>{selected.name}</strong> (N° {selected.number})
        </span>
        <button type="button" onClick={() => onSelect(null)}>
          Cambiar cliente
        </button>
      </div>
    );
  }

  if (creating) {
    return (
      <div className="card form-card">
        <ClientForm
          idPrefix="order-new-client"
          title="Nuevo cliente"
          initial={{ ...EMPTY_CLIENT, name: text.trim() }}
          submitLabel="Crear cliente"
          isPending={createClient.isPending}
          error={createClient.error}
          onSubmit={(values) => createClient.mutate(values, { onSuccess: choose })}
        />
        <button type="button" onClick={() => setCreating(false)}>
          Volver a la lista
        </button>
      </div>
    );
  }

  const page = options.data;
  const more = page ? page.total - page.items.length : 0;

  return (
    <div className="clients__form orders__client-picker" onBlur={closeWhenFocusLeaves}>
      <label htmlFor="order-client">Cliente</label>
      <input
        id="order-client"
        value={text}
        onChange={(event) => {
          setText(event.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onClick={() => setOpen(true)}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            setOpen(false);
          }
        }}
        placeholder="Elegí de la lista o escribí el nombre o número"
        autoComplete="off"
        role="combobox"
        aria-expanded={open}
        aria-controls="order-client-options"
      />
      {open && (
        <div id="order-client-options" className="orders__client-options">
          {options.isError && <p role="alert">No se pudieron buscar los clientes.</p>}
          {options.isLoading && <p>Buscando clientes…</p>}
          {page && page.items.length === 0 && (
            <p>{search.trim() ? "No hay clientes con ese nombre." : "Todavía no hay clientes."}</p>
          )}
          {page && page.items.length > 0 && (
            <ul className="clients__contact-list">
              {page.items.map((client) => (
                <li key={client.id}>
                  <button
                    type="button"
                    aria-label={`Elegir ${client.name} (N° ${client.number})`}
                    onClick={() => choose(client)}
                  >
                    {client.name} (N° {client.number})
                  </button>
                </li>
              ))}
            </ul>
          )}
          {more > 0 && <p>Hay {more} clientes más: seguí escribiendo para encontrarlo.</p>}
          <button type="button" onClick={() => setCreating(true)}>
            Crear cliente nuevo
          </button>
        </div>
      )}
    </div>
  );
}
