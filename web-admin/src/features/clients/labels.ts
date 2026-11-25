import type {
  ClientSegment,
  Equipment,
  PowerSupply,
  Refrigerant,
  Site,
  TaxCondition,
} from "./types";

export const SEGMENT_LABELS: Record<ClientSegment, string> = {
  unclassified: "Sin clasificar",
  private_person: "Particular",
  business: "Comercio",
  government: "Estado",
  healthcare: "Sanatorio o clínica",
  hotel: "Hotel",
};

export const TAX_CONDITION_LABELS: Record<TaxCondition, string> = {
  final_consumer: "Consumidor final",
  registered_taxpayer: "Responsable inscripto",
  monotributo: "Monotributo",
};

/** Cómo se nombra un domicilio en la pantalla: la etiqueta o, si no tiene, la dirección. */
export function siteName(site: Pick<Site, "label" | "address">): string {
  return site.label ?? site.address;
}

export function equipmentCountLabel(count: number): string {
  return count === 1 ? "1 equipo" : `${count} equipos`;
}

// Datos técnicos del equipo (E03-10), en el orden en que se ofrecen.
export const REFRIGERANT_LABELS: Record<Refrigerant, string> = {
  R22: "R22",
  R410A: "R410A",
  R32: "R32",
  R407C: "R407C",
  R404A: "R404A",
  R134a: "R134a",
  R290: "R290",
  other: "Otro",
};

export const POWER_SUPPLY_LABELS: Record<PowerSupply, string> = {
  "220": "220 V (monofásica)",
  "380": "380 V (trifásica)",
};

/** "3000 frigorías · R410A · 220 V", con lo que haya cargado; null si no hay nada. */
export function technicalSummary(
  equipment: Pick<Equipment, "capacity_frigorias" | "refrigerant" | "power_supply">,
): string | null {
  const parts = [
    equipment.capacity_frigorias != null &&
      `${equipment.capacity_frigorias.toLocaleString("es-AR")} frigorías`,
    equipment.refrigerant && `Gas ${REFRIGERANT_LABELS[equipment.refrigerant]}`,
    equipment.power_supply && `${equipment.power_supply} V`,
  ].filter((part): part is string => Boolean(part));
  return parts.length ? parts.join(" · ") : null;
}
