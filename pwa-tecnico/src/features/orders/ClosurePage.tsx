import { ChevronLeft } from "lucide-react";
import { useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  EMPTY_DRAFT,
  OTHER,
  asksEquipmentCondition,
  failureRepairRequired,
  missingFields,
  observationRequired,
  repairsFor,
  toClosurePayload,
  type ClosureDraft,
  type ClosureErrors,
  type ClosureField,
  type ClosureOptions,
} from "./closure";
import { EQUIPMENT_CONDITIONS, NOT_DONE_REASONS } from "./labels";
import { useCloseOrder } from "./useCloseOrder";
import { useClosureOptions } from "./useClosureOptions";
import { useOrderDetail } from "./useOrderDetail";

/** Aviso que la lista muestra al volver de un cierre. */
export interface ClosedNotice {
  notice: string;
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
  observation: "closure-observation",
};
const FIELD_ORDER = Object.keys(SECTION_OF) as ClosureField[];

function isClosureField(field: string): field is ClosureField {
  return field in SECTION_OF;
}

export function ClosurePage() {
  const { orderId = "" } = useParams();
  const order = useOrderDetail(orderId);
  const options = useClosureOptions(orderId);

  let body: ReactNode;
  if (options.isPending) {
    body = <p className="orders__message">Cargando el cierre…</p>;
  } else if (options.isError) {
    body = (
      <p className="orders__message" role="alert">
        No se pudo cargar el cierre. Revisá la conexión.
      </p>
    );
  } else if (options.data === null) {
    body = <NotFound />;
  } else {
    body = (
      <ClosureForm orderId={orderId} orderNumber={order.data?.number} options={options.data} />
    );
  }

  return (
    <main className="orders">
      <Link to={`/ordenes/${orderId}`} className="order-detail__back">
        <ChevronLeft size={20} aria-hidden="true" />
        Volver a la orden
      </Link>
      <header className="closure__header">
        <h1>Cerrar orden{order.data ? ` N° ${order.data.number}` : ""}</h1>
        {order.data && (
          <p>
            {order.data.work_type_name} · {order.data.client_name}
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

interface ClosureFormProps {
  orderId: string;
  orderNumber: number | undefined;
  options: ClosureOptions;
}

function ClosureForm({ orderId, orderNumber, options }: ClosureFormProps) {
  const navigate = useNavigate();
  const close = useCloseOrder(orderId);
  const [draft, setDraft] = useState<ClosureDraft>(EMPTY_DRAFT);
  // Una clave por cierre: los reintentos del mismo envío no lo duplican (E05-12).
  const [idempotencyKey, setIdempotencyKey] = useState(() => crypto.randomUUID());
  const [submitted, setSubmitted] = useState(false);
  const [serverError, setServerError] = useState<{ field: string; message: string } | null>(null);
  const [notFound, setNotFound] = useState(false);

  if (notFound) {
    return <NotFound />;
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

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    setSubmitted(true);
    setServerError(null);
    const missing = missingFields(draft, options);
    if (Object.keys(missing).length > 0) {
      focusFirst(missing);
      return;
    }
    close.mutate(toClosurePayload(draft, idempotencyKey), {
      onSuccess: (result) => {
        if (result.kind === "not_found") {
          setNotFound(true);
        } else if (result.kind === "invalid") {
          if (result.code === "idempotency_key_reused") {
            setIdempotencyKey(crypto.randomUUID());
          }
          setServerError({ field: result.field, message: result.message });
          if (isClosureField(result.field)) {
            focusFirst({ [result.field]: result.message });
          }
        } else {
          const number = orderNumber !== undefined ? ` N° ${orderNumber}` : "";
          const notice =
            result.closure.order_status === "done"
              ? `Orden${number} cerrada.`
              : `Orden${number} devuelta a la oficina.`;
          navigate("/", { replace: true, state: { notice } satisfies ClosedNotice });
        }
      },
    });
  };

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
    <form className="closure" onSubmit={onSubmit} noValidate>
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
      {close.isError && (
        <p className="closure__error" role="alert">
          No se pudo enviar el cierre. Revisá la conexión e intentá de nuevo.
        </p>
      )}
      <button type="submit" className="closure__submit" disabled={close.isPending}>
        {close.isPending
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
