import {
  EQUIPMENT_CONDITION_LABELS,
  formatDate,
  formatDateTime,
  NO_SIGNATURE_REASON_LABELS,
  NOT_DONE_REASON_LABELS,
  OUTCOME_LABELS,
} from "./labels";
import type { ClosureDetail as Closure, OrderListItem } from "./types";
import { useOrderClosure } from "./useOrders";

/** Lo que cargó la escuadrilla al cerrar, para revisarlo antes de facturar (E04-08). */
export function ClosureDetail({ order }: { order: OrderListItem }) {
  const closure = useOrderClosure(order.id);
  const label = `Cierre de la orden N° ${order.number}`;

  if (closure.isLoading) {
    return <p>Cargando el cierre…</p>;
  }
  if (closure.isError || !closure.data) {
    return <p role="alert">No se pudo cargar el cierre.</p>;
  }
  const data = closure.data;
  const rows: [string, string | null][] = [
    ["Resultado", OUTCOME_LABELS[data.outcome]],
    ["Escuadrilla", data.crew_name],
    ["Cerrada el", `${formatDate(data.closed_at)} por ${data.closed_by_name}`],
    ["Fueron", data.technicians.join(", ") || null],
    ["Tareas", data.tasks.join(", ") || null],
    ["Falla", data.failure],
    ["Reparación", data.repair],
    [
      "Estado del equipo",
      data.equipment_condition && EQUIPMENT_CONDITION_LABELS[data.equipment_condition],
    ],
    ["Motivo", data.not_done_reason && NOT_DONE_REASON_LABELS[data.not_done_reason]],
    ["Observación", data.observation],
  ];

  return (
    <dl className="orders__closure" aria-label={label}>
      {rows
        .filter((row): row is [string, string] => Boolean(row[1]))
        .map(([term, value]) => (
          <div key={term}>
            <dt>{term}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      {data.photos.length > 0 && (
        <div className="orders__closure-photos-row">
          <dt>Fotos</dt>
          <dd>
            {/* E05-06, criterio 6: miniatura y, al tocarla, la foto grande en otra pestaña. */}
            <ul className="orders__closure-photos">
              {data.photos.map((photo, index) => (
                <li key={photo.id}>
                  <a href={photo.url} target="_blank" rel="noopener noreferrer">
                    <img src={photo.url} alt={`Foto ${index + 1} del cierre`} loading="lazy" />
                  </a>
                </li>
              ))}
            </ul>
          </dd>
        </div>
      )}
      <SignatureRow closure={data} />
    </dl>
  );
}

/**
 * E05-07, criterio 6: la firma del cliente con su nombre y la hora, o el motivo por el
 * que no hay. Los cierres anteriores a la firma no tienen ninguna de las dos.
 */
function SignatureRow({ closure }: { closure: Closure }) {
  const { signature, no_signature_reason: reason, no_signature_text: text } = closure;
  if (signature) {
    return (
      <div className="orders__closure-signature-row">
        <dt>Firma</dt>
        <dd>
          <a href={signature.url} target="_blank" rel="noopener noreferrer">
            <img
              className="orders__closure-signature"
              src={signature.url}
              alt={`Firma de ${signature.signer_name}`}
              loading="lazy"
            />
          </a>
          <p className="orders__closure-signer">
            {signature.signer_name} · {formatDateTime(signature.signed_at)}
          </p>
        </dd>
      </div>
    );
  }
  if (!reason) {
    return null;
  }
  return (
    <div>
      <dt>Sin firma</dt>
      <dd>{reason === "other" && text ? text : NO_SIGNATURE_REASON_LABELS[reason]}</dd>
    </div>
  );
}
