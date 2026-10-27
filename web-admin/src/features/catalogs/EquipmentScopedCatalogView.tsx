import type { UseMutationResult, UseQueryResult } from "@tanstack/react-query";
import { useId, type ReactNode } from "react";

import { useEquipmentTypes } from "../equipment-types/useEquipmentTypes";
import { CatalogItem } from "./CatalogItem";
import { NewNameForm } from "./NewNameForm";
import { PageHeader } from "../../app/PageHeader";

/** Valor de un catálogo de un tipo de equipo, o genérico (sin tipo): fallas y reparaciones. */
interface ScopedItem {
  id: string;
  name: string;
  is_active: boolean;
  equipment_type_id: string | null;
}

type ItemChanges = { name?: string | null; is_active?: boolean | null };

interface Texts {
  title: string;
  newItem: string;
  submit: string;
  showInactive: string;
  loading: string;
  loadError: string;
  empty: string;
  nameTaken: string;
}

interface EquipmentScopedCatalogViewProps<T extends ScopedItem> {
  texts: Texts;
  /** null = genéricos: aplican a todos los tipos de equipo. */
  equipmentTypeId: string | null;
  onEquipmentTypeChange: (equipmentTypeId: string | null) => void;
  showInactive: boolean;
  onShowInactiveChange: (showInactive: boolean) => void;
  items: UseQueryResult<T[]>;
  /** Alta habilitada, o el motivo por el que todavía no se puede dar de alta. */
  create:
    | {
        isPending: boolean;
        error: Error | null;
        onCreate: (name: string, reset: () => void) => void;
      }
    | { disabledReason: string };
  useUpdate: (id: string) => UseMutationResult<T, Error, ItemChanges>;
  /** Filtros propios del catálogo (por ejemplo, la falla de las reparaciones). */
  filters?: ReactNode;
  /** Etiquetas propias de cada valor, además de "Genérica". */
  badges?: (item: T) => ReactNode;
}

export function EquipmentScopedCatalogView<T extends ScopedItem>({
  texts,
  equipmentTypeId,
  onEquipmentTypeChange,
  showInactive,
  onShowInactiveChange,
  items,
  create,
  useUpdate,
  filters,
  badges,
}: EquipmentScopedCatalogViewProps<T>) {
  const titleId = useId();
  // También los tipos desactivados, para poder administrar sus valores.
  const equipmentTypes = useEquipmentTypes(true);

  // Sin tipo elegido la API trae todos; la vista de genéricos se queda con los que no tienen tipo.
  const visible =
    equipmentTypeId === null
      ? items.data?.filter((item) => item.equipment_type_id === null)
      : items.data;

  return (
    <section className="catalog" aria-labelledby={titleId}>
      <PageHeader eyebrow="Catálogos" title={texts.title} titleId={titleId} />

      <label className="catalog__toggle">
        Tipo de equipo
        <select
          value={equipmentTypeId ?? ""}
          onChange={(event) => onEquipmentTypeChange(event.target.value || null)}
        >
          <option value="">Genéricas</option>
          {equipmentTypes.data?.map((equipmentType) => (
            <option key={equipmentType.id} value={equipmentType.id}>
              {equipmentType.is_active ? equipmentType.name : `${equipmentType.name} (desactivado)`}
            </option>
          ))}
        </select>
      </label>

      {filters}

      {"disabledReason" in create ? (
        <p className="catalog__hint">{create.disabledReason}</p>
      ) : (
        <NewNameForm
          label={texts.newItem}
          submitLabel={texts.submit}
          isPending={create.isPending}
          error={create.error}
          nameTakenMessage={texts.nameTaken}
          onCreate={create.onCreate}
        />
      )}

      <label className="catalog__toggle">
        <input
          type="checkbox"
          checked={showInactive}
          onChange={(event) => onShowInactiveChange(event.target.checked)}
        />
        {texts.showInactive}
      </label>

      {items.isLoading && <p>{texts.loading}</p>}
      {items.isError && <p role="alert">{texts.loadError}</p>}

      {visible && visible.length === 0 && <p>{texts.empty}</p>}
      {visible && visible.length > 0 && (
        <ul className="catalog__list" aria-label={texts.title}>
          {visible.map((item) => (
            <ScopedCatalogItem
              key={item.id}
              item={item}
              useUpdate={useUpdate}
              nameTaken={texts.nameTaken}
            >
              {equipmentTypeId !== null && item.equipment_type_id === null && (
                <span className="catalog__badge">Genérica</span>
              )}
              {badges?.(item)}
            </ScopedCatalogItem>
          ))}
        </ul>
      )}
    </section>
  );
}

function ScopedCatalogItem<T extends ScopedItem>({
  item,
  useUpdate,
  nameTaken,
  children,
}: {
  item: T;
  useUpdate: (id: string) => UseMutationResult<T, Error, ItemChanges>;
  nameTaken: string;
  children: ReactNode;
}) {
  const update = useUpdate(item.id);
  return (
    <CatalogItem
      name={item.name}
      isActive={item.is_active}
      isPending={update.isPending}
      error={update.error}
      nameTakenMessage={nameTaken}
      onSave={(changes) => update.mutate(changes)}
    >
      {children}
    </CatalogItem>
  );
}
