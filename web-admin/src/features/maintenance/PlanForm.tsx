import { useState, type FormEvent } from "react";

import type { ClientSummary } from "../clients/types";
import { useEquipment, useSites } from "../clients/useClients";
import { useCrews } from "../crews/useCrews";
import { ClientPicker } from "../orders/ClientPicker";
import { activeSites } from "../orders/formValues";
import { businessToday } from "../orders/labels";
import { SitePicker } from "../orders/SitePicker";
import { useWorkTypes } from "../work-types/useWorkTypes";
import { EVERY_OPTIONS, everyText } from "./labels";
import type { MaintenancePlan } from "./types";
import { useCreatePlan, useUpdatePlan } from "./useMaintenance";

// El tipo de trabajo que se propone para los planes nuevos (el de mantenimiento de Persat).
const DEFAULT_WORK_TYPE = "service";

interface PlanFormProps {
  /** Sin plan, es el alta. */
  plan?: MaintenancePlan;
  onDone: () => void;
}

interface Values {
  workTypeId: string;
  crewId: string;
  everyMonths: number;
  nextDueOn: string;
  endsOn: string;
  notes: string;
}

function initialValues(plan: MaintenancePlan | undefined): Values {
  return {
    workTypeId: plan?.work_type.id ?? "",
    crewId: plan?.crew?.id ?? "",
    everyMonths: plan?.every_months ?? 3,
    nextDueOn: plan?.next_due_on ?? "",
    endsOn: plan?.ends_on ?? "",
    notes: plan?.notes ?? "",
  };
}

/** Alta o edición de un plan (E07-03). El equipo se elige solo en el alta. */
export function PlanForm({ plan, onDone }: PlanFormProps) {
  const [client, setClient] = useState<ClientSummary | null>(null);
  const [siteId, setSiteId] = useState("");
  const [equipmentId, setEquipmentId] = useState("");
  const [values, setValues] = useState<Values>(() => initialValues(plan));
  const [missing, setMissing] = useState<string | null>(null);
  const sites = useSites(client?.id ?? "", { enabled: client !== null });
  const active = activeSites(sites.data);
  const site = active.length === 1 ? active[0].id : siteId;
  const equipment = useEquipment(client?.id ?? "", site || null);
  const workTypes = useWorkTypes(false);
  const crews = useCrews(false);
  const create = useCreatePlan();
  const update = useUpdatePlan(plan?.id ?? "");
  const mutation = plan ? update : create;
  const set = (changes: Partial<Values>) => setValues({ ...values, ...changes });
  const prefix = `plan-${plan?.id ?? "new"}`;
  const workTypeId =
    values.workTypeId ||
    (plan
      ? ""
      : (workTypes.data?.find((type) => type.name.toLowerCase() === DEFAULT_WORK_TYPE)?.id ?? ""));

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const faltan = [
      !plan && !equipmentId && "el equipo",
      !workTypeId && "el tipo de trabajo",
      !values.nextDueOn && "la próxima visita",
    ].filter((item): item is string => Boolean(item));
    const last = faltan.at(-1);
    const rest = faltan.slice(0, -1);
    setMissing(last ? `Falta ${rest.length ? `${rest.join(", ")} y ${last}` : last}.` : null);
    if (faltan.length) {
      return;
    }
    const common = {
      work_type_id: workTypeId,
      crew_id: values.crewId || null,
      every_months: values.everyMonths,
      next_due_on: values.nextDueOn,
      ends_on: values.endsOn || null,
      notes: values.notes.trim() || null,
    };
    if (plan) {
      update.mutate(common, { onSuccess: onDone });
    } else {
      create.mutate({ ...common, equipment_id: equipmentId }, { onSuccess: onDone });
    }
  }

  return (
    <section className="orders__new" aria-label={plan ? "Editar plan" : "Nuevo plan"}>
      <h3>{plan ? `Plan de ${plan.equipment.internal_code}` : "Nuevo plan"}</h3>
      {!plan && (
        <>
          <ClientPicker
            selected={client}
            onSelect={(elegido) => {
              setClient(elegido);
              setSiteId("");
              setEquipmentId("");
            }}
          />
          {client && (
            <SitePicker
              clientId={client.id}
              sites={sites}
              value={site}
              onChange={(id) => {
                setSiteId(id);
                setEquipmentId("");
              }}
            />
          )}
        </>
      )}
      <form className="clients__form" onSubmit={handleSubmit} aria-label="Datos del plan">
        {!plan && client && site && (
          <>
            <label htmlFor={`${prefix}-equipment`}>Equipo</label>
            <select
              id={`${prefix}-equipment`}
              value={equipmentId}
              onChange={(event) => setEquipmentId(event.target.value)}
            >
              <option value="">Elegí un equipo</option>
              {(equipment.data ?? []).map((item) => (
                <option key={item.id} value={item.id}>
                  {item.internal_code} · {item.location_note}
                </option>
              ))}
            </select>
            {equipment.data?.length === 0 && (
              <p className="muted">Este domicilio no tiene equipos cargados.</p>
            )}
          </>
        )}
        <label htmlFor={`${prefix}-every`}>Frecuencia</label>
        <select
          id={`${prefix}-every`}
          value={values.everyMonths}
          onChange={(event) => set({ everyMonths: Number(event.target.value) })}
        >
          {EVERY_OPTIONS.map((months) => (
            <option key={months} value={months}>
              {everyText(months)}
            </option>
          ))}
        </select>
        <label htmlFor={`${prefix}-next`}>Próxima visita</label>
        <input
          id={`${prefix}-next`}
          type="date"
          min={plan ? undefined : businessToday()}
          value={values.nextDueOn}
          onChange={(event) => set({ nextDueOn: event.target.value })}
        />
        <label htmlFor={`${prefix}-crew`}>Escuadrilla que suele ir (opcional)</label>
        <select
          id={`${prefix}-crew`}
          value={values.crewId}
          onChange={(event) => set({ crewId: event.target.value })}
        >
          <option value="">Sin escuadrilla fija</option>
          {(crews.data ?? []).map((crew) => (
            <option key={crew.id} value={crew.id}>
              {crew.name}
            </option>
          ))}
        </select>
        <label htmlFor={`${prefix}-work-type`}>Tipo de trabajo</label>
        <select
          id={`${prefix}-work-type`}
          value={workTypeId}
          onChange={(event) => set({ workTypeId: event.target.value })}
        >
          <option value="">Elegí un tipo</option>
          {(workTypes.data ?? []).map((type) => (
            <option key={type.id} value={type.id}>
              {type.name}
            </option>
          ))}
        </select>
        <label htmlFor={`${prefix}-ends`}>Fin del abono (opcional)</label>
        <input
          id={`${prefix}-ends`}
          type="date"
          value={values.endsOn}
          onChange={(event) => set({ endsOn: event.target.value })}
        />
        <label htmlFor={`${prefix}-notes`}>Indicaciones para la escuadrilla (opcional)</label>
        <textarea
          id={`${prefix}-notes`}
          maxLength={500}
          value={values.notes}
          onChange={(event) => set({ notes: event.target.value })}
        />
        <p className="muted">
          Una semana antes de cada visita se genera la orden, Pendiente, y la próxima visita se
          corre sola.
        </p>
        {missing && (
          <p className="clients__error" role="alert">
            {missing}
          </p>
        )}
        {mutation.isError && (
          <p className="clients__error" role="alert">
            {mutation.error.message}
          </p>
        )}
        <div className="users__actions">
          <button type="submit" disabled={mutation.isPending}>
            {plan ? "Guardar plan" : "Crear plan"}
          </button>
          <button type="button" onClick={onDone}>
            Cancelar
          </button>
        </div>
      </form>
    </section>
  );
}
