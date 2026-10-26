import type { ClientSegment, TaxCondition } from "./types";

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
