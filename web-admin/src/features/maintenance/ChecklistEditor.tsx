import { useState } from "react";

import { CatalogItem } from "../catalogs/CatalogItem";
import { NewNameForm } from "../catalogs/NewNameForm";
import type { CheckStep } from "./types";
import {
  useCheckSteps,
  useCreateCheckStep,
  useReorderCheckSteps,
  useUpdateCheckStep,
} from "./useChecklist";

const NAME_TAKEN = "Ya hay un paso con ese nombre (puede estar desactivado).";

/**
 * Checklist único de mantenimiento (E07-01): la escuadrilla marca cada paso OK o No OK.
 * Cada orden se lleva los pasos activos al generarse; cambiarlos acá no toca las ya
 * generadas.
 */
export function ChecklistEditor() {
  const [showInactive, setShowInactive] = useState(false);
  const steps = useCheckSteps(showInactive);
  const create = useCreateCheckStep();
  const reorder = useReorderCheckSteps();
  const active = steps.data?.filter((step) => step.is_active) ?? [];

  function move(stepId: string, offset: -1 | 1) {
    const ids = active.map((step) => step.id);
    const from = ids.indexOf(stepId);
    const to = from + offset;
    [ids[from], ids[to]] = [ids[to], ids[from]];
    reorder.mutate(ids);
  }

  return (
    <section className="catalog" aria-label="Checklist de mantenimiento">
      <h2>Checklist de mantenimiento</h2>
      <p className="muted">
        Los pasos que la escuadrilla marca OK o No OK en cada visita. Los cambios valen para las
        órdenes que se generen desde ahora.
      </p>
      <NewNameForm
        label="Paso nuevo"
        submitLabel="Agregar paso"
        isPending={create.isPending}
        error={create.error}
        nameTakenMessage={NAME_TAKEN}
        onCreate={(name, reset) => create.mutate(name, { onSuccess: reset })}
      />
      <label className="catalog__toggle">
        <input
          type="checkbox"
          checked={showInactive}
          onChange={(event) => setShowInactive(event.target.checked)}
        />
        Ver también los desactivados
      </label>
      {steps.isLoading && <p>Cargando el checklist…</p>}
      {steps.isError && <p role="alert">No se pudo cargar el checklist.</p>}
      {reorder.isError && <p role="alert">{reorder.error.message}</p>}
      {steps.data?.length === 0 && <p>Sin pasos: las visitas se cierran sin checklist.</p>}
      <ol className="catalog__list" aria-label="Pasos del checklist">
        {steps.data?.map((step) => {
          const index = active.indexOf(step);
          return (
            <StepItem
              key={step.id}
              step={step}
              canMoveUp={index > 0}
              canMoveDown={index >= 0 && index < active.length - 1}
              moving={reorder.isPending}
              onMove={(offset) => move(step.id, offset)}
            />
          );
        })}
      </ol>
    </section>
  );
}

interface StepItemProps {
  step: CheckStep;
  canMoveUp: boolean;
  canMoveDown: boolean;
  moving: boolean;
  onMove: (offset: -1 | 1) => void;
}

function StepItem({ step, canMoveUp, canMoveDown, moving, onMove }: StepItemProps) {
  const update = useUpdateCheckStep(step.id);
  return (
    <CatalogItem
      name={step.name}
      isActive={step.is_active}
      isPending={update.isPending}
      error={update.error}
      nameTakenMessage={NAME_TAKEN}
      onSave={(changes) => update.mutate(changes)}
    >
      {step.is_active && (
        <div className="users__actions">
          <button
            type="button"
            aria-label={`Subir ${step.name}`}
            disabled={!canMoveUp || moving}
            onClick={() => onMove(-1)}
          >
            Subir
          </button>
          <button
            type="button"
            aria-label={`Bajar ${step.name}`}
            disabled={!canMoveDown || moving}
            onClick={() => onMove(1)}
          >
            Bajar
          </button>
        </div>
      )}
    </CatalogItem>
  );
}
