import type { Equipment } from "../clients/types";
import { useEquipment } from "../clients/useClients";
import { useEquipmentTypes } from "../equipment-types/useEquipmentTypes";

interface EquipmentSelectProps {
  id: string;
  clientId: string;
  siteId: string;
  /** "" sin equipo. */
  value: string;
  onChange: (equipmentId: string) => void;
}

/** "EA1 · Aire acondicionado · Sala de máquinas · Marca Modelo". */
function equipmentLabel(equipment: Equipment, typeName: string | undefined): string {
  const brandModel = [equipment.brand, equipment.model].filter(Boolean).join(" ");
  return [equipment.internal_code, typeName, equipment.location_note, brandModel]
    .filter(Boolean)
    .join(" · ");
}

/** El equipo de la orden: opcional, solo los del domicilio elegido (E04-12). */
export function EquipmentSelect({ id, clientId, siteId, value, onChange }: EquipmentSelectProps) {
  const equipment = useEquipment(clientId, siteId);
  // Con los inactivos: un equipo puede ser de un tipo que después se desactivó.
  const types = useEquipmentTypes(true);
  const typeName = (typeId: string) => types.data?.find((type) => type.id === typeId)?.name;
  const items = equipment.data ?? [];

  return (
    <>
      <label htmlFor={id}>Equipo (opcional)</label>
      <select
        id={id}
        value={value}
        disabled={equipment.isLoading}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">Sin equipo</option>
        {items.map((item) => (
          <option key={item.id} value={item.id}>
            {equipmentLabel(item, typeName(item.equipment_type_id))}
          </option>
        ))}
      </select>
      {equipment.isError && (
        <p className="clients__error" role="alert">
          No se pudieron cargar los equipos del domicilio.
        </p>
      )}
      {equipment.data && items.length === 0 && (
        <p className="muted">Este domicilio no tiene equipos cargados.</p>
      )}
    </>
  );
}
