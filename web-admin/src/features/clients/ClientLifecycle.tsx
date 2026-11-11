import { useState } from "react";

import { ClientPicker } from "../orders/ClientPicker";
import { formatDateTime } from "../orders/labels";
import type { Client, ClientSummary } from "./types";
import { useClientAudit, useClientLifecycle, useMergeClient, useMergePreview } from "./useClients";

const AUDIT_LABELS: Record<string, string> = {
  deactivated: "Dado de baja",
  restored: "Restaurado",
  merged: "Unificado en otro cliente",
  merged_in: "Recibió otro cliente",
};

/**
 * Baja y restauración (E03-07) y unificación en otro cliente (E03-08). La unificación
 * muestra antes qué se va a mover y pide confirmarla.
 */
export function ClientLifecycle({ client }: { client: Client }) {
  const lifecycle = useClientLifecycle(client.id);
  const audit = useClientAudit(client.id);
  const [merging, setMerging] = useState(false);
  const deleted = Boolean(client.deleted_at);

  return (
    <section className="clients__contacts" aria-label="Baja y unificación">
      <h4>Baja y unificación</h4>
      {client.merged_into && (
        <p role="note">
          Dado de baja: se unificó en el cliente N° {client.merged_into.number} (
          {client.merged_into.name}).
        </p>
      )}
      {deleted && !client.merged_into && <p role="note">Dado de baja. Su historial se conserva.</p>}
      {!deleted && (
        <div className="clients__filters">
          <button
            type="button"
            className="btn--danger"
            disabled={lifecycle.isPending}
            onClick={() => lifecycle.mutate("deactivation")}
          >
            Dar de baja
          </button>
          <button type="button" onClick={() => setMerging((open) => !open)}>
            {merging ? "Cancelar unificación" : "Unificar en otro cliente"}
          </button>
        </div>
      )}
      {deleted && !client.merged_into && (
        <button
          type="button"
          disabled={lifecycle.isPending}
          onClick={() => lifecycle.mutate("restoration")}
        >
          Restaurar
        </button>
      )}
      {lifecycle.isError && (
        <p className="clients__error" role="alert">
          {lifecycle.error.message}
        </p>
      )}
      {merging && !deleted && <MergeForm client={client} onDone={() => setMerging(false)} />}
      {audit.data && audit.data.length > 0 && (
        <ul className="clients__contact-list" aria-label="Auditoría del cliente">
          {audit.data.map((entry, index) => (
            <li key={index}>
              {formatDateTime(entry.occurred_at)} · {AUDIT_LABELS[entry.action] ?? entry.action}
              {entry.actor_name && ` · ${entry.actor_name}`}
              {entry.detail && ` · ${entry.detail}`}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function MergeForm({ client, onDone }: { client: Client; onDone: () => void }) {
  const [target, setTarget] = useState<ClientSummary | null>(null);
  const preview = useMergePreview(client.id, target?.id ?? null);
  const merge = useMergeClient(client.id);

  return (
    <div className="clients__form" aria-label={`Unificar ${client.name} en otro cliente`}>
      <p className="muted">
        Elegí el cliente que queda. Todo lo de {client.name} pasa a ese cliente y este queda dado de
        baja. Los equipos conservan su código.
      </p>
      <ClientPicker selected={target} onSelect={setTarget} />
      {preview.isError && (
        <p className="clients__error" role="alert">
          {preview.error.message}
        </p>
      )}
      {preview.data && (
        <>
          <p>
            Pasan a N° {preview.data.target_number} ({preview.data.target_name}):{" "}
            {preview.data.sites} domicilios, {preview.data.equipment} equipos,{" "}
            {preview.data.contacts} contactos y {preview.data.orders} órdenes.
          </p>
          {merge.isError && (
            <p className="clients__error" role="alert">
              {merge.error.message}
            </p>
          )}
          <button
            type="button"
            className="btn--danger"
            disabled={merge.isPending}
            onClick={() => merge.mutate(preview.data.target_id, { onSuccess: onDone })}
          >
            Confirmar unificación
          </button>
        </>
      )}
    </div>
  );
}
