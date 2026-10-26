import { useState } from "react";

import { EquipmentScopedCatalogView } from "../catalogs/EquipmentScopedCatalogView";
import { useCreateFailure, useFailures, useUpdateFailure } from "./useFailures";

const TEXTS = {
  title: "Fallas",
  newItem: "Nueva falla",
  submit: "Agregar falla",
  showInactive: "Mostrar desactivadas",
  loading: "Cargando fallas…",
  loadError: "No se pudieron cargar las fallas.",
  empty: "Todavía no hay fallas.",
  nameTaken:
    "Ya existe una falla con ese nombre para ese tipo de equipo o como genérica (puede estar desactivada).",
};

export function FailuresPage() {
  const [equipmentTypeId, setEquipmentTypeId] = useState<string | null>(null);
  const [showInactive, setShowInactive] = useState(false);
  const failures = useFailures(equipmentTypeId, showInactive);
  const create = useCreateFailure();

  return (
    <EquipmentScopedCatalogView
      texts={TEXTS}
      equipmentTypeId={equipmentTypeId}
      onEquipmentTypeChange={setEquipmentTypeId}
      showInactive={showInactive}
      onShowInactiveChange={setShowInactive}
      items={failures}
      create={{
        isPending: create.isPending,
        error: create.error,
        onCreate: (name, reset) =>
          create.mutate({ name, equipment_type_id: equipmentTypeId }, { onSuccess: reset }),
      }}
      useUpdate={useUpdateFailure}
    />
  );
}
