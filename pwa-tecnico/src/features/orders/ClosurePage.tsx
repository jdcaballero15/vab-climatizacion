import { useQueryClient } from "@tanstack/react-query";
import { ChevronLeft } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { ClosurePhotos } from "./ClosurePhotos";
import {
  EMPTY_DRAFT,
  OTHER,
  asksEquipmentCondition,
  failureRepairRequired,
  missingFields,
  observationRequired,
  repairsFor,
  restoreDraft,
  type ClosureDraft,
  type ClosureErrors,
  type ClosureField,
  type ClosureOptions,
} from "./closure";
import {
  deleteClosureDraft,
  saveClosureDraft,
  type ClosureProblem,
  type StoredClosure,
  type StoredOrderSummary,
} from "./closureDrafts";
import { schedulePendingClosures } from "./closureRetry";
import { sendClosure } from "./closureSender";
import { EQUIPMENT_CONDITIONS, NOT_DONE_REASONS } from "./labels";
import { MAX_PHOTOS, PhotoUploadError, compressImage, type ClosurePhoto } from "./photos";
import { useStoredClosure } from "./useClosureDrafts";
import { useClosureOptions } from "./useClosureOptions";
import { forgetClosedOrder } from "./useMyOrders";
import { useOrderDetail } from "./useOrderDetail";

/** Aviso que la lista muestra al volver de un cierre. */
export interface ClosedNotice {
  notice: string;
  /** Quedó pendiente de enviar (E05-13): se muestra como aviso, no como éxito. */
  pending?: boolean;
  /** Orden del cierre pendiente y qué decir cuando el reintento lo manda. */
  orderId?: string;
  sentNotice?: string;
}

// Sección del formulario de cada campo, en el orden en que se muestran.
const SECTION_OF: Record<ClosureField, string> = {
  technician_ids: "closure-technicians",
  task_ids: "closure-tasks",
  outcome: "closure-outcome",
  not_done_reason: "closure-outcome",
  failure_id: "closure-failure",
  failure_other_text: "closure-failure",
  repair_id: "closure-repair",
  repair_other_text: "closure-repair",
  equipment_condition: "closure-equipment",
  photo_ids: "closure-photos",
  observation: "closure-observation",
};
const FIELD_ORDER = Object.keys(SECTION_OF) as ClosureField[];

function isClosureField(field: string): field is ClosureField {
  return field in SECTION_OF;
}

interface ClosurePageProps {
  /** Usuario de la sesión: el borrador es suyo (E05-13). */
  userId: string;
}

export function ClosurePage({ userId }: ClosurePageProps) {
  const { orderId = "" } = useParams();
  const order = useOrderDetail(orderId);
  const options = useClosureOptions(orderId);
  const stored = useStoredClosure(userId, orderId);
  // La orden rechazada ya no tiene detalle: se muestra con lo que quedó guardado.
  const summary: StoredOrderSummary | null = order.data
    ? {
        number: order.data.number,
        workTypeName: order.data.work_type_name,
        clientName: order.data.client_name,
      }
    : (stored?.order ?? null);

  // Una orden rechazada ya no tiene detalle al que volver.
  const gone = stored?.status === "rejected" || options.data === null;

  let body: ReactNode;
  const loading = <p className="orders__message">Cargando el cierre…</p>;
  if (stored === undefined) {
    body = loading;
  } else if (stored?.status === "rejected") {
    body = <RejectedClosure userId={userId} orderId={orderId} problem={stored.problem} />;
  } else if (options.isPending) {
    body = loading;
  } else if (options.isError) {
    body = (
      <div className="orders__message" role="alert">
        <p>No se pudo cargar el cierre. Revisá la conexión.</p>
        {stored?.status === "pending" && (
          <p>El cierre quedó guardado y se envía solo cuando vuelva la señal.</p>
        )}
      </div>
    );
  } else if (options.data === null) {
    // Un borrador de una orden que la oficina canceló o reasignó: no se pierde sin avisar.
    body = stored ? (
      <RejectedClosure userId={userId} orderId={orderId} problem={null} />
    ) : (
      <NotFound />
    );
  } else {
    body = (
      <ClosureForm
        userId={userId}
        orderId={orderId}
        summary={summary}
        options={options.data}
        stored={stored}
      />
    );
  }

  return (
    <main className="orders">
      <Link to={gone ? "/" : `/ordenes/${orderId}`} className="order-detail__back">
        <ChevronLeft size={20} aria-hidden="true" />
        {gone ? "Volver a la lista" : "Volver a la orden"}
      </Link>
      <header className="closure__header">
        <h1>Cerrar orden{summary ? ` N° ${summary.number}` : ""}</h1>
        {summary && (
          <p>
            {summary.workTypeName} · {summary.clientName}
          </p>
        )}
      </header>
      {body}
    </main>
  );
}

function NotFound() {
  return (
    <div className="orders__message">
      <p>Esta orden ya no está en curso para tu escuadrilla.</p>
      <p>Puede que ya se haya cerrado o que la hayan reasignado. Volvé a la lista.</p>
    </div>
  );
}

interface RejectedClosureProps {
  userId: string;
  orderId: string;
  problem: ClosureProblem | null;
}

/**
 * E05-13, criterio 6: la oficina canceló o reasignó la orden. Lo cargado queda en el
 * celular hasta que el técnico lo descarte, con confirmación.
 */
function RejectedClosure({ userId, orderId, problem }: RejectedClosureProps) {
  const navigate = useNavigate();
  const [confirming, setConfirming] = useState(false);
  const [discarding, setDiscarding] = useState(false);

  const discard = async () => {
    setDiscarding(true);
    await deleteClosureDraft(userId, orderId);
    navigate("/", {
      replace: true,
      state: { notice: "Cierre descartado." } satisfies ClosedNotice,
    });
  };

  return (
    <div className="closure__rejected">
      <p className="closure__rejected-title" role="alert">
        Rechazado: avisale a la oficina
      </p>
      <p>{problem?.message ?? "Esta orden ya no está en curso para tu escuadrilla."}</p>
      <p>Lo que cargaste sigue guardado en este celular hasta que lo descartes.</p>
      {confirming ? (
        <div
          className="order-start order-start--confirm"
          role="group"
          aria-label="Confirmar descarte"
        >
          <p className="order-start__question">¿Descartar el cierre?</p>
          <p className="closure__hint">Se borra del celular lo cargado, con sus fotos.</p>
          <div className="order-start__actions">
            <button
              type="button"
              className="order-start__primary"
              disabled={discarding}
              onClick={() => void discard()}
            >
              Sí, descartar
            </button>
            <button
              type="button"
              className="order-start__secondary"
              disabled={discarding}
              onClick={() => setConfirming(false)}
            >
              Cancelar
            </button>
          </div>
        </div>
      ) : (
        <button
          type="button"
          className="order-start__secondary"
          onClick={() => setConfirming(true)}
        >
          Descartar cierre
        </button>
      )}
    </div>
  );
}

interface ClosureFormProps {
  userId: string;
  orderId: string;
  summary: StoredOrderSummary | null;
  options: ClosureOptions;
  /** Lo que quedó guardado en el celular de una vez anterior (E05-13). */
  stored: StoredClosure | null;
}

function ClosureForm({ userId, orderId, summary, options, stored }: ClosureFormProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  // Lo que se cargó al abrir: mientras nada cambie, no hay nada nuevo que guardar.
  const [initial] = useState(() => ({
    draft: stored ? restoreDraft(stored.draft, options) : EMPTY_DRAFT,
    // Una clave por cierre: los reintentos del mismo envío no lo duplican (E05-12).
    idempotencyKey: stored?.idempotencyKey ?? crypto.randomUUID(),
    photos: (stored?.photos ?? []).map((photo): ClosurePhoto => ({
      ...photo,
      previewUrl: URL.createObjectURL(photo.blob),
    })),
  }));
  const [draft, setDraft] = useState<ClosureDraft>(initial.draft);
  const [idempotencyKey, setIdempotencyKey] = useState(initial.idempotencyKey);
  const [submitted, setSubmitted] = useState(false);
  // E05-13, criterio 7: un 422 de un envío anterior vuelve marcado en el formulario.
  const [serverError, setServerError] = useState<ClosureProblem | null>(stored?.problem ?? null);
  const [rejected, setRejected] = useState<ClosureProblem | null>(null);
  const [photos, setPhotos] = useState<ClosurePhoto[]>(initial.photos);
  const [addingPhotos, setAddingPhotos] = useState(false);
  const [photoNotice, setPhotoNotice] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  // Las miniaturas ocupan memoria hasta que se liberan: al salir del formulario se sueltan.
  const photosRef = useRef(photos);
  photosRef.current = photos;
  useEffect(
    () => () => photosRef.current.forEach((photo) => URL.revokeObjectURL(photo.previewUrl)),
    [],
  );

  // E05-13, criterio 1: cada cambio queda en el celular, sin tocar ningún botón. Un cambio
  // en un cierre pendiente lo vuelve borrador: se manda cuando el técnico toque enviar.
  // Mientras se envía, lo guardado lo maneja el envío.
  const handedOff = useRef(false);
  useEffect(() => {
    const unchanged =
      draft === initial.draft &&
      photos === initial.photos &&
      idempotencyKey === initial.idempotencyKey;
    if (unchanged || handedOff.current) {
      return;
    }
    void saveClosureDraft({
      userId,
      orderId,
      status: "draft",
      problem: serverError,
      order: summary,
      draft,
      idempotencyKey,
      photos,
    });
  }, [userId, orderId, summary, draft, photos, idempotencyKey, serverError, initial]);

  if (rejected) {
    return <RejectedClosure userId={userId} orderId={orderId} problem={rejected} />;
  }

  const errors: ClosureErrors = submitted ? missingFields(draft, options) : {};
  if (serverError && isClosureField(serverError.field) && !errors[serverError.field]) {
    errors[serverError.field] = serverError.message;
  }
  const generalError =
    serverError && !isClosureField(serverError.field) ? serverError.message : null;
  const errorList = FIELD_ORDER.flatMap((field) => errors[field] ?? []);

  const update = (changes: Partial<ClosureDraft>) => {
    setServerError(null);
    setDraft((current) => ({ ...current, ...changes }));
  };
  const toggle = (list: string[], id: string) =>
    list.includes(id) ? list.filter((item) => item !== id) : [...list, id];

  const focusFirst = (missing: ClosureErrors) => {
    const first = FIELD_ORDER.find((field) => missing[field]);
    if (first) {
      document.getElementById(SECTION_OF[first])?.focus();
    }
  };

  const addPhotos = async (files: File[]) => {
    setServerError(null);
    const room = MAX_PHOTOS - photos.length;
    setPhotoNotice(files.length > room ? `Podés adjuntar hasta ${MAX_PHOTOS} fotos.` : null);
    setAddingPhotos(true);
    try {
      for (const file of files.slice(0, room)) {
        const blob = await compressImage(file);
        const photo: ClosurePhoto = {
          key: crypto.randomUUID(),
          blob,
          previewUrl: URL.createObjectURL(blob),
          fileId: null,
          uploaded: false,
        };
        setPhotos((current) => [...current, photo]);
      }
    } catch (error) {
      setPhotoNotice(
        error instanceof PhotoUploadError ? error.message : "No se pudo abrir la foto.",
      );
    } finally {
      setAddingPhotos(false);
    }
  };

  const removePhoto = (key: string) => {
    setServerError(null);
    setPhotoNotice(null);
    setPhotos((current) => {
      const removed = current.find((photo) => photo.key === key);
      if (removed) {
        URL.revokeObjectURL(removed.previewUrl);
      }
      return current.filter((photo) => photo.key !== key);
    });
  };

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitted(true);
    setServerError(null);
    const missing = missingFields(draft, options);
    if (Object.keys(missing).length > 0) {
      focusFirst(missing);
      return;
    }
    handedOff.current = true;
    setSending(true);
    const result = await sendClosure({
      userId,
      orderId,
      status: "pending",
      problem: null,
      order: summary,
      draft,
      idempotencyKey,
      photos,
    });
    const number = summary ? ` N° ${summary.number}` : "";
    if (result.kind === "closed") {
      forgetClosedOrder(queryClient, orderId);
      const notice =
        result.closure.order_status === "done"
          ? `Orden${number} cerrada.`
          : `Orden${number} devuelta a la oficina.`;
      navigate("/", { replace: true, state: { notice } satisfies ClosedNotice });
    } else if (result.kind === "offline") {
      // E05-13, criterio 3: queda pendiente y se manda solo cuando vuelve la señal.
      schedulePendingClosures();
      const notice = `Sin señal. El cierre de la orden${number} quedó pendiente y se envía solo cuando vuelva la señal.`;
      const sentNotice = `Se envió el cierre de la orden${number}.`;
      navigate("/", {
        replace: true,
        state: { notice, pending: true, orderId, sentNotice } satisfies ClosedNotice,
      });
    } else if (result.kind === "rejected") {
      setRejected(result.stored.problem);
    } else {
      // Lo que el envío ya hizo (fotos subidas, clave nueva) pasa al formulario.
      const { stored: saved } = result;
      setIdempotencyKey(saved.idempotencyKey);
      setPhotos((current) =>
        current.map((photo) => {
          const match = saved.photos.find((item) => item.key === photo.key);
          return match ? { ...photo, fileId: match.fileId, uploaded: match.uploaded } : photo;
        }),
      );
      setServerError(saved.problem);
      handedOff.current = false;
      setSending(false);
      if (saved.problem && isClosureField(saved.problem.field)) {
        focusFirst({ [saved.problem.field]: saved.problem.message });
      }
    }
  };

  const busy = sending;
  const required = failureRepairRequired(draft, options);
  const repairs = repairsFor(draft, options);
  let step = 0;
  const title = (text: string, extra?: ReactNode, id?: string) => (
    <h2 className="closure__title" id={id}>
      <span className="closure__step" aria-hidden="true">
        {++step}
      </span>
      {text}
      {extra}
    </h2>
  );
  const optionalTag = (isRequired: boolean) => (
    <span className="closure__tag">{isRequired ? " (obligatoria)" : " (opcional)"}</span>
  );

  return (
    <form className="closure" onSubmit={(event) => void onSubmit(event)} noValidate>
      {stored?.status === "pending" ? (
        <p className="closure__restored closure__restored--pending" role="status">
          Pendiente de enviar: se envía solo cuando vuelva la señal. Si cambiás algo, tocá de nuevo
          el botón de abajo.
        </p>
      ) : (
        stored && (
          <p className="closure__restored" role="status">
            Se recuperó lo que habías cargado en este celular.
          </p>
        )
      )}
      <Section id="closure-technicians" error={errors.technician_ids}>
        {title("¿Quiénes fueron?")}
        <div className="closure__choices closure__choices--cols">
          {options.technicians.map((technician) => (
            <Choice
              key={technician.id}
              pressed={draft.technicianIds.includes(technician.id)}
              onClick={() => update({ technicianIds: toggle(draft.technicianIds, technician.id) })}
            >
              {technician.name}
            </Choice>
          ))}
        </div>
        {options.technicians.length === 0 && (
          <p className="closure__hint">No hay técnicos cargados. Avisale a administración.</p>
        )}
      </Section>

      <Section id="closure-tasks" error={errors.task_ids}>
        {title("Tareas")}
        {options.tasks.length > 0 ? (
          <>
            <p className="closure__hint">Tildá las que hicieron.</p>
            <div className="closure__choices">
              {options.tasks.map((task) => (
                <Choice
                  key={task.id}
                  pressed={draft.taskIds.includes(task.id)}
                  onClick={() => update({ taskIds: toggle(draft.taskIds, task.id) })}
                >
                  {task.name}
                </Choice>
              ))}
            </div>
          </>
        ) : (
          <p className="closure__hint">Este tipo de trabajo no tiene tareas cargadas.</p>
        )}
      </Section>

      <Section id="closure-outcome" error={errors.outcome ?? errors.not_done_reason}>
        {title("Resultado")}
        <p className="closure__group">Se hizo</p>
        <div className="closure__choices">
          <Choice
            single
            pressed={draft.outcome === "done"}
            onClick={() => update({ outcome: "done", notDoneReason: null })}
          >
            Resuelta
          </Choice>
          <Choice
            single
            pressed={draft.outcome === "needs_revisit"}
            onClick={() => update({ outcome: "needs_revisit", notDoneReason: null })}
          >
            Requiere otra visita
          </Choice>
        </div>
        <p className="closure__group">No se pudo hacer</p>
        <div className="closure__choices">
          {NOT_DONE_REASONS.map(([reason, label]) => (
            <Choice
              key={reason}
              single
              fail
              pressed={draft.outcome === "not_done" && draft.notDoneReason === reason}
              onClick={() => update({ outcome: "not_done", notDoneReason: reason })}
            >
              {label}
            </Choice>
          ))}
        </div>
      </Section>

      <Section id="closure-failure" error={errors.failure_id ?? errors.failure_other_text}>
        {title("Falla", optionalTag(required), "closure-failure-title")}
        <select
          aria-labelledby="closure-failure-title"
          className="closure__select"
          value={draft.failure}
          onChange={(event) =>
            update({ failure: event.target.value, failureOther: "", repair: "", repairOther: "" })
          }
        >
          <option value="">Elegí la falla</option>
          {options.failures.map((failure) => (
            <option key={failure.id} value={failure.id}>
              {failure.name}
            </option>
          ))}
          <option value={OTHER}>Otro</option>
        </select>
        {draft.failure === OTHER && (
          <OtherText
            label="¿Cuál es la falla?"
            value={draft.failureOther}
            onChange={(failureOther) => update({ failureOther })}
          />
        )}
      </Section>

      <Section id="closure-repair" error={errors.repair_id ?? errors.repair_other_text}>
        {title("Reparación", optionalTag(required), "closure-repair-title")}
        <select
          aria-labelledby="closure-repair-title"
          className="closure__select"
          value={draft.repair}
          disabled={draft.failure === ""}
          onChange={(event) => update({ repair: event.target.value, repairOther: "" })}
        >
          <option value="">
            {draft.failure === "" ? "Elegí primero la falla" : "Elegí la reparación"}
          </option>
          {repairs.map((repair) => (
            <option key={repair.id} value={repair.id}>
              {repair.name}
            </option>
          ))}
          <option value={OTHER}>Otro</option>
        </select>
        {draft.repair === OTHER && (
          <OtherText
            label="¿Cuál es la reparación?"
            value={draft.repairOther}
            onChange={(repairOther) => update({ repairOther })}
          />
        )}
      </Section>

      {asksEquipmentCondition(draft) && (
        <Section id="closure-equipment" error={errors.equipment_condition}>
          {title("¿Cómo quedó el equipo?")}
          <div className="closure__choices">
            {EQUIPMENT_CONDITIONS.map(([condition, label]) => (
              <Choice
                key={condition}
                single
                fail={condition === "not_working"}
                pressed={draft.equipmentCondition === condition}
                onClick={() => update({ equipmentCondition: condition })}
              >
                {label}
              </Choice>
            ))}
          </div>
        </Section>
      )}

      <Section id="closure-photos" error={errors.photo_ids}>
        {title("Fotos", optionalTag(false))}
        <ClosurePhotos
          photos={photos}
          adding={addingPhotos}
          notice={photoNotice}
          disabled={busy}
          onAdd={(files) => void addPhotos(files)}
          onRemove={removePhoto}
        />
      </Section>

      <Section id="closure-observation" error={errors.observation}>
        {title("Observación", optionalTag(observationRequired(draft)), "closure-observation-title")}
        {draft.outcome === "needs_revisit" && (
          <p className="closure__hint">Contá qué falta para terminar el trabajo.</p>
        )}
        <textarea
          aria-labelledby="closure-observation-title"
          className="closure__text"
          rows={4}
          maxLength={2000}
          value={draft.observation}
          aria-invalid={errors.observation ? true : undefined}
          onChange={(event) => update({ observation: event.target.value })}
        />
      </Section>

      {errorList.length > 0 && (
        <div className="closure__missing" role="alert">
          <p>Falta completar:</p>
          <ul>
            {errorList.map((message) => (
              <li key={message}>{message}</li>
            ))}
          </ul>
        </div>
      )}
      {generalError && (
        <p className="closure__error" role="alert">
          {generalError}
        </p>
      )}

      <button type="submit" className="closure__submit" disabled={busy || addingPhotos}>
        {sending
          ? "Enviando…"
          : draft.outcome === "not_done"
            ? "Cerrar como no realizada"
            : "Finalizar orden"}
      </button>
    </form>
  );
}

interface SectionProps {
  id: string;
  error: string | undefined;
  children: ReactNode;
}

/** Tarjeta del formulario. Enfocable para llevar la pantalla al primer faltante. */
function Section({ id, error, children }: SectionProps) {
  return (
    <section
      id={id}
      tabIndex={-1}
      className={error ? "closure__section closure__section--invalid" : "closure__section"}
      aria-describedby={error ? `${id}-error` : undefined}
    >
      {children}
      {error && (
        <p id={`${id}-error`} className="closure__field-error">
          {error}
        </p>
      )}
    </section>
  );
}

interface ChoiceProps {
  pressed: boolean;
  onClick: () => void;
  fail?: boolean;
  /** Opción única (resultado, estado del equipo): punto en lugar de tilde. */
  single?: boolean;
  children: ReactNode;
}

/** Opción grande para tildar con un dedo, como en el prototipo del cliente. */
function Choice({ pressed, onClick, fail = false, single = false, children }: ChoiceProps) {
  const className = [
    "closure__choice",
    fail && "closure__choice--fail",
    single && "closure__choice--single",
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <button type="button" className={className} aria-pressed={pressed} onClick={onClick}>
      <span className="closure__box" aria-hidden="true">
        {pressed && !single ? "✓" : ""}
      </span>
      <span>{children}</span>
    </button>
  );
}

interface OtherTextProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
}

function OtherText({ label, value, onChange }: OtherTextProps) {
  return (
    <label className="closure__other">
      {label}
      <input
        type="text"
        className="closure__input"
        maxLength={255}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}
