import type { Site } from "../clients/types";
import type { OrderChannel, OrderKind } from "./types";

export interface OrderFormValues {
  clientId: string | null;
  siteId: string;
  workTypeId: string;
  channel: OrderChannel | "";
  description: string;
  requesterName: string;
  requesterArea: string;
  /** "" sin equipo (E04-12). */
  equipmentId: string;
  /** Taller (E06-01): retiro, galpón y devolución en una sola orden. */
  kind: OrderKind;
}

export const EMPTY_ORDER: OrderFormValues = {
  clientId: null,
  siteId: "",
  workTypeId: "",
  channel: "",
  description: "",
  requesterName: "",
  requesterArea: "",
  equipmentId: "",
  kind: "on_site",
};

export function activeSites(sites: Site[] | undefined): Site[] {
  return (sites ?? []).filter((site) => site.is_active);
}

/** Lo obligatorio que falta, en una frase; null si está completo. El backend también lo valida. */
export function missingFields(values: OrderFormValues): string | null {
  const missing = [
    !values.clientId && "el cliente",
    values.clientId && !values.siteId && "el domicilio",
    !values.workTypeId && "el tipo de trabajo",
    !values.channel && "el canal",
    values.description.trim() === "" && "la descripción",
  ].filter((item): item is string => Boolean(item));
  if (missing.length === 0) {
    return null;
  }
  const last = missing.pop();
  return `Falta ${missing.length ? `${missing.join(", ")} y ${last}` : last}.`;
}
