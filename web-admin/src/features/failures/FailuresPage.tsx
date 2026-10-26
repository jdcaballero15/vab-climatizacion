import { useState } from "react";

import { CatalogItem } from "../catalogs/CatalogItem";
import { NewNameForm } from "../catalogs/NewNameForm";
import { useEquipmentTypes } from "../equipment-types/useEquipmentTypes";
import type { Failure } from "./types";
import { useCreateFailure, useFailures, useUpdateFailure } from "./useFailures";

const NAME_TAKEN =
  "Ya existe una falla con ese nombre para ese tipo de equipo o como genérica (puede estar desactivada).";

export function FailuresPage() {
  // null = genéricas: aplican a todos los tipos de equipo.
  const [equipmentTypeId, setEquipmentTypeId] = useState<string | null>(null);
  const [showInactive, setShowInactive] = useState(false);
  // También los tipos desactivados, para poder administrar sus fallas.
  const equipmentTypes = useEquipmentTypes(true);
  const failures = useFailures(equipmentTypeId, showInactive);
  const create = useCreateFailure();

  // Sin tipo elegido la API trae todas; la vista de genéricas se queda con las que no tienen tipo.
  const visible =
    equipmentTypeId === null
      ? failures.data?.filter((failure) => failure.equipment_type_id === null)
      : failures.data;

  return (
    <section className="catalog">
      <h2>Fallas</h2>

      <label className="catalog__toggle">
        Tipo de equipo
        <select
          value={equipmentTypeId ?? ""}
          onChange={(event) => setEquipmentTypeId(event.target.value || null)}
        >
          <option value="">Genéricas</option>
          {equipmentTypes.data?.map((equipmentType) => (
            <option key={equipmentType.id} value={equipmentType.id}>
              {equipmentType.is_active ? equipmentType.name : `${equipmentType.name} (desactivado)`}
            </option>
          ))}
        </select>
      </label>

      <NewNameForm
        label="Nueva falla"
        submitLabel="Agregar falla"
        isPending={create.isPending}
        error={create.error}
        nameTakenMessage={NAME_TAKEN}
        onCreate={(name, reset) =>
          create.mutate({ name, equipment_type_id: equipmentTypeId }, { onSuccess: reset })
        }
      />

      <label className="catalog__toggle">
        <input
          type="checkbox"
          checked={showInactive}
          onChange={(event) => setShowInactive(event.target.checked)}
        />
        Mostrar desactivadas
      </label>

      {failures.isLoading && <p>Cargando fallas…</p>}
      {failures.isError && <p role="alert">No se pudieron cargar las fallas.</p>}

      {visible && visible.length === 0 && <p>Todavía no hay fallas.</p>}
      {visible && visible.length > 0 && (
        <ul className="catalog__list" aria-label="Fallas">
          {visible.map((failure) => (
            <FailureItem
              key={failure.id}
              failure={failure}
              markGeneric={equipmentTypeId !== null && failure.equipment_type_id === null}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

function FailureItem({ failure, markGeneric }: { failure: Failure; markGeneric: boolean }) {
  const update = useUpdateFailure(failure.id);
  return (
    <CatalogItem
      name={failure.name}
      isActive={failure.is_active}
      isPending={update.isPending}
      error={update.error}
      nameTakenMessage={NAME_TAKEN}
      onSave={(changes) => update.mutate(changes)}
    >
      {markGeneric && <span className="catalog__badge">Genérica</span>}
    </CatalogItem>
  );
}
