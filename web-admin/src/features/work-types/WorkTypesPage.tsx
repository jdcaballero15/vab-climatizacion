import { useState } from "react";

import { CatalogItem } from "./CatalogItem";
import { NewNameForm } from "./NewNameForm";
import type { Task, WorkType } from "./types";
import {
  useCreateTask,
  useCreateWorkType,
  useTasks,
  useUpdateTask,
  useUpdateWorkType,
  useWorkTypes,
} from "./useWorkTypes";

const WORK_TYPE_TAKEN = "Ya existe un tipo de trabajo con ese nombre (puede estar desactivado).";
const TASK_TAKEN =
  "Este tipo de trabajo ya tiene una subtarea con ese nombre (puede estar desactivada).";

export function WorkTypesPage() {
  const [showInactive, setShowInactive] = useState(false);
  const workTypes = useWorkTypes(showInactive);
  const createWorkType = useCreateWorkType();

  return (
    <section className="catalog">
      <h2>Tipos de trabajo</h2>

      <NewNameForm
        label="Nuevo tipo de trabajo"
        submitLabel="Agregar tipo"
        isPending={createWorkType.isPending}
        error={createWorkType.error}
        nameTakenMessage={WORK_TYPE_TAKEN}
        onCreate={(name, reset) => createWorkType.mutate(name, { onSuccess: reset })}
      />

      <label className="catalog__toggle">
        <input
          type="checkbox"
          checked={showInactive}
          onChange={(event) => setShowInactive(event.target.checked)}
        />
        Mostrar desactivados
      </label>

      {workTypes.isLoading && <p>Cargando tipos de trabajo…</p>}
      {workTypes.isError && <p role="alert">No se pudieron cargar los tipos de trabajo.</p>}

      {workTypes.data && (
        <ul className="catalog__list">
          {workTypes.data.map((workType) => (
            <WorkTypeItem key={workType.id} workType={workType} showInactive={showInactive} />
          ))}
        </ul>
      )}
    </section>
  );
}

function WorkTypeItem({ workType, showInactive }: { workType: WorkType; showInactive: boolean }) {
  const update = useUpdateWorkType(workType.id);
  const [open, setOpen] = useState(false);

  return (
    <CatalogItem
      name={workType.name}
      isActive={workType.is_active}
      isPending={update.isPending}
      error={update.error}
      nameTakenMessage={WORK_TYPE_TAKEN}
      onSave={(changes) => update.mutate(changes)}
    >
      <button
        type="button"
        className="catalog__expand"
        aria-expanded={open}
        aria-label={`Subtareas de ${workType.name}`}
        onClick={() => setOpen(!open)}
      >
        {open ? "Ocultar subtareas" : "Ver subtareas"}
      </button>
      {open && <TaskList workTypeId={workType.id} showInactive={showInactive} />}
    </CatalogItem>
  );
}

function TaskList({ workTypeId, showInactive }: { workTypeId: string; showInactive: boolean }) {
  const tasks = useTasks(workTypeId, showInactive);
  const createTask = useCreateTask(workTypeId);

  return (
    <div className="catalog__tasks">
      <NewNameForm
        label="Nueva subtarea"
        submitLabel="Agregar subtarea"
        isPending={createTask.isPending}
        error={createTask.error}
        nameTakenMessage={TASK_TAKEN}
        onCreate={(name, reset) => createTask.mutate(name, { onSuccess: reset })}
      />
      {tasks.isLoading && <p>Cargando subtareas…</p>}
      {tasks.isError && <p role="alert">No se pudieron cargar las subtareas.</p>}
      {tasks.data && tasks.data.length === 0 && <p>Sin subtareas.</p>}
      {tasks.data && tasks.data.length > 0 && (
        <ul className="catalog__list">
          {tasks.data.map((task) => (
            <TaskItem key={task.id} task={task} />
          ))}
        </ul>
      )}
    </div>
  );
}

function TaskItem({ task }: { task: Task }) {
  const update = useUpdateTask(task.work_type_id, task.id);
  return (
    <CatalogItem
      name={task.name}
      isActive={task.is_active}
      isPending={update.isPending}
      error={update.error}
      nameTakenMessage={TASK_TAKEN}
      onSave={(changes) => update.mutate(changes)}
    />
  );
}
