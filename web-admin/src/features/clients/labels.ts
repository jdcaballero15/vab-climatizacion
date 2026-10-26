import type { ClientSegment, TaxCondition } from "./types";

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
