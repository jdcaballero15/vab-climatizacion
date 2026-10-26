import { useState } from "react";

import { CatalogItem } from "../work-types/CatalogItem";
import { NewNameForm } from "../work-types/NewNameForm";
import type { EquipmentType } from "./types";
import {
  useCreateEquipmentType,
  useEquipmentTypes,
  useUpdateEquipmentType,
} from "./useEquipmentTypes";

const NAME_TAKEN = "Ya existe un tipo de equipo con ese nombre (puede estar desactivado).";

export function EquipmentTypesPage() {
  const [showInactive, setShowInactive] = useState(false);
  const equipmentTypes = useEquipmentTypes(showInactive);
  const create = useCreateEquipmentType();

  return (
    <section className="catalog">
      <h2>Tipos de equipo</h2>

      <NewNameForm
        label="Nuevo tipo de equipo"
        submitLabel="Agregar tipo"
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
        Mostrar desactivados
      </label>

      {equipmentTypes.isLoading && <p>Cargando tipos de equipo…</p>}
      {equipmentTypes.isError && <p role="alert">No se pudieron cargar los tipos de equipo.</p>}

      {/* Puede quedar vacío si administración desactiva todos los tipos. */}
      {equipmentTypes.data && equipmentTypes.data.length === 0 && (
        <p>Todavía no hay tipos de equipo.</p>
      )}
      {equipmentTypes.data && equipmentTypes.data.length > 0 && (
        <ul className="catalog__list">
          {equipmentTypes.data.map((equipmentType) => (
            <EquipmentTypeItem key={equipmentType.id} equipmentType={equipmentType} />
          ))}
        </ul>
      )}
    </section>
  );
}

function EquipmentTypeItem({ equipmentType }: { equipmentType: EquipmentType }) {
  const update = useUpdateEquipmentType(equipmentType.id);
  return (
    <CatalogItem
      name={equipmentType.name}
      isActive={equipmentType.is_active}
      isPending={update.isPending}
      error={update.error}
      nameTakenMessage={NAME_TAKEN}
      onSave={(changes) => update.mutate(changes)}
    />
  );
}
