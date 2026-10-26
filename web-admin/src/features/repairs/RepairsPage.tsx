import { useState } from "react";

import { EquipmentScopedCatalogView } from "../catalogs/EquipmentScopedCatalogView";
import { useFailures } from "../failures/useFailures";
import { useCreateRepair, useRepairs, useUpdateRepair } from "./useRepairs";

const TEXTS = {
  title: "Reparaciones",
  newItem: "Nueva reparación",
  submit: "Agregar reparación",
  showInactive: "Mostrar desactivadas",
  loading: "Cargando reparaciones…",
  loadError: "No se pudieron cargar las reparaciones.",
  empty: "Todavía no hay reparaciones.",
  nameTaken:
    "Ya existe una reparación con ese nombre para ese tipo de equipo o como genérica (puede estar desactivada).",
};

export function RepairsPage() {
  const [equipmentTypeId, setEquipmentTypeId] = useState<string | null>(null);
  // null = todas las fallas. Para dar de alta hay que elegir una.
  const [failureId, setFailureId] = useState<string | null>(null);
  const [showInactive, setShowInactive] = useState(false);
  // Solo las fallas que aplican al tipo elegido (las suyas y las genéricas), para que no se
  // pueda elegir una incompatible. En "Genéricas", solo las genéricas.
  const failures = useFailures(equipmentTypeId, true);
  const applicableFailures =
    equipmentTypeId === null
      ? failures.data?.filter((failure) => failure.equipment_type_id === null)
      : failures.data;
  const failureNames = new Map(failures.data?.map((failure) => [failure.id, failure.name]));
  const repairs = useRepairs(equipmentTypeId, failureId, showInactive);
  // Una falla desactivada no ofrece reparaciones: la lista vacía no significa que no haya.
  const selectedFailureInactive =
    failures.data?.find((failure) => failure.id === failureId)?.is_active === false;
  const create = useCreateRepair();

  function changeEquipmentType(next: string | null) {
    setEquipmentTypeId(next);
    // La falla elegida puede no aplicar al tipo nuevo.
    setFailureId(null);
  }

  return (
    <EquipmentScopedCatalogView
      texts={
        selectedFailureInactive && !showInactive
          ? {
              ...TEXTS,
              empty:
                "La falla elegida está desactivada y no ofrece reparaciones. Marcá «Mostrar desactivadas» para verlas.",
            }
          : TEXTS
      }
      equipmentTypeId={equipmentTypeId}
      onEquipmentTypeChange={changeEquipmentType}
      showInactive={showInactive}
      onShowInactiveChange={setShowInactive}
      items={repairs}
      filters={
        <label className="catalog__toggle">
          Falla
          <select
            value={failureId ?? ""}
            onChange={(event) => setFailureId(event.target.value || null)}
          >
            <option value="">Todas</option>
            {applicableFailures?.map((failure) => (
              <option key={failure.id} value={failure.id}>
                {failure.is_active ? failure.name : `${failure.name} (desactivada)`}
              </option>
            ))}
          </select>
        </label>
      }
      create={
        failureId === null
          ? { disabledReason: "Elegí una falla para agregar reparaciones." }
          : {
              isPending: create.isPending,
              error: create.error,
              onCreate: (name, reset) =>
                create.mutate(
                  { name, equipment_type_id: equipmentTypeId, failure_id: failureId },
                  { onSuccess: reset },
                ),
            }
      }
      useUpdate={useUpdateRepair}
      badges={(repair) =>
        failureId === null && (
          <span className="catalog__badge">{failureNames.get(repair.failure_id)}</span>
        )
      }
    />
  );
}
