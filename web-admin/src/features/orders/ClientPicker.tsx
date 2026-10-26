import { useState } from "react";

import type { ClientSummary } from "../clients/types";
import { MIN_CLIENT_SEARCH, useClientSearch } from "./useOrders";

interface ClientPickerProps {
  selected: ClientSummary | null;
  onSelect: (client: ClientSummary | null) => void;
}

/** Busca el cliente por nombre; hasta elegir uno se muestran los resultados. */
export function ClientPicker({ selected, onSelect }: ClientPickerProps) {
  const [text, setText] = useState("");
  const search = useClientSearch(text);
  const tooShort = text.trim().length < MIN_CLIENT_SEARCH;

  if (selected) {
    return (
      <div className="orders__client">
        <span>
          Cliente: <strong>{selected.name}</strong> (N° {selected.number})
        </span>
        <button
          type="button"
          onClick={() => {
            setText("");
            onSelect(null);
          }}
        >
          Cambiar cliente
        </button>
      </div>
    );
  }

  return (
    <div className="clients__form">
      <label htmlFor="order-client">Cliente</label>
      <input
        id="order-client"
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder="Nombre del cliente"
        autoComplete="off"
      />
      {text !== "" && tooShort && <p>Escribí al menos {MIN_CLIENT_SEARCH} letras del nombre.</p>}
      {!tooShort && search.isError && <p role="alert">No se pudieron buscar los clientes.</p>}
      {!tooShort && search.data?.length === 0 && <p>No hay clientes con ese nombre.</p>}
      {!tooShort && search.data && search.data.length > 0 && (
        <ul className="clients__contact-list">
          {search.data.map((client) => (
            <li key={client.id}>
              <button
                type="button"
                aria-label={`Elegir ${client.name} (N° ${client.number})`}
                onClick={() => {
                  // Al volver a buscar (otro cliente u otra orden) se arranca de cero.
                  setText("");
                  onSelect(client);
                }}
              >
                {client.name} (N° {client.number})
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
