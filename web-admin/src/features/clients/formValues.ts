import type { ClientSegment, SiteCreate, TaxCondition } from "./types";

export interface ClientFormValues {
  name: string;
  segment: ClientSegment;
  tax_id: string | null;
  tax_condition: TaxCondition | null;
  notes: string | null;
}

export const EMPTY_CLIENT: ClientFormValues = {
  name: "",
  segment: "unclassified",
  tax_id: null,
  tax_condition: null,
  notes: null,
};

export const EMPTY_SITE: SiteCreate = { label: null, address: "", reference: null };

// El backend también la rechaza; acá se evita el viaje y se avisa en el formulario.
export function missingAddress(values: SiteCreate): boolean {
  return values.address.trim() === "";
}
