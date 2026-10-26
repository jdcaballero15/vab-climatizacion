import { useState, type FormEvent } from "react";

import { SEGMENT_LABELS, TAX_CONDITION_LABELS } from "./labels";
import type { ClientFormValues } from "./formValues";
import type { ClientSegment, ClientSummary, TaxCondition } from "./types";
import { fetchSimilarClients } from "./useClients";

interface ClientFormProps {
  /** Prefijo de los id de los campos: hay un formulario de alta y otro de edición a la vez. */
  idPrefix: string;
  title: string;
  initial: ClientFormValues;
  /** Al editar, el propio cliente no cuenta como parecido. */
  excludeId?: string;
  submitLabel: string;
  isPending: boolean;
  error: Error | null;
  onSubmit: (values: ClientFormValues, reset: () => void) => void;
}

/** Alta o edición de los datos de un cliente. Avisa si el nombre se parece a otro. */
export function ClientForm({
  idPrefix,
  title,
  initial,
  excludeId,
  submitLabel,
  isPending,
  error,
  onSubmit,
}: ClientFormProps) {
  const [values, setValues] = useState(initial);
  const [similar, setSimilar] = useState<ClientSummary[] | null>(null);
  const [checkError, setCheckError] = useState(false);

  const id = (field: string) => `${idPrefix}-${field}`;

  function set<K extends keyof ClientFormValues>(field: K, value: ClientFormValues[K]) {
    setValues((current) => ({ ...current, [field]: value }));
    setSimilar(null);
  }

  function save() {
    setSimilar(null);
    onSubmit(values, () => setValues(initial));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCheckError(false);
    // Solo se busca parecidos si el nombre es nuevo o cambió; nunca bloquea el guardado.
    if (values.name.trim() === initial.name.trim()) {
      save();
      return;
    }
    try {
      const found = await fetchSimilarClients(values.name, excludeId);
      if (found.length > 0) {
        setSimilar(found);
        return;
      }
    } catch {
      setCheckError(true);
      return;
    }
    save();
  }

  return (
    <form className="clients__form" onSubmit={handleSubmit} aria-label={title}>
      <h3>{title}</h3>

      <label htmlFor={id("name")}>Nombre o razón social</label>
      <input
        id={id("name")}
        value={values.name}
        onChange={(event) => set("name", event.target.value)}
        required
        maxLength={255}
      />

      <label htmlFor={id("segment")}>Segmento</label>
      <select
        id={id("segment")}
        value={values.segment}
        onChange={(event) => set("segment", event.target.value as ClientSegment)}
      >
        {Object.entries(SEGMENT_LABELS).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>

      <label htmlFor={id("tax_id")}>CUIT o DNI</label>
      <input
        id={id("tax_id")}
        value={values.tax_id ?? ""}
        onChange={(event) => set("tax_id", event.target.value || null)}
        maxLength={20}
      />

      <label htmlFor={id("tax_condition")}>Condición fiscal</label>
      <select
        id={id("tax_condition")}
        value={values.tax_condition ?? ""}
        onChange={(event) => set("tax_condition", (event.target.value || null) as TaxCondition)}
      >
        <option value="">Sin dato</option>
        {Object.entries(TAX_CONDITION_LABELS).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>

      <label htmlFor={id("notes")}>Observaciones</label>
      <textarea
        id={id("notes")}
        value={values.notes ?? ""}
        onChange={(event) => set("notes", event.target.value || null)}
        maxLength={2000}
      />

      {similar && (
        <div className="clients__warning" role="alert">
          <p>Hay clientes con un nombre parecido:</p>
          <ul>
            {similar.map((client) => (
              <li key={client.id}>
                {client.name} (N° {client.number})
              </li>
            ))}
          </ul>
          <p>¿Es otro cliente?</p>
          <button type="button" onClick={save} disabled={isPending}>
            Guardar igual
          </button>
          <button type="button" onClick={() => setSimilar(null)}>
            Cancelar
          </button>
        </div>
      )}

      {checkError && (
        <p className="clients__error" role="alert">
          No se pudo verificar si el cliente ya existe. Probá de nuevo.
        </p>
      )}
      {error && (
        <p className="clients__error" role="alert">
          {error.message}
        </p>
      )}

      {!similar && (
        <button type="submit" disabled={isPending}>
          {isPending ? "Guardando…" : submitLabel}
        </button>
      )}
    </form>
  );
}
