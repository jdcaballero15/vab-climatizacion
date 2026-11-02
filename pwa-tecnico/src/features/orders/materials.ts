import type { components } from "../../api/schema";

export type PartChoice = components["schemas"]["PartChoiceTechnicianOut"];

/** Un material cargado en el cierre (E05-05). `part` es el id del material u OTHER. */
export interface MaterialDraft {
  /** Identifica la línea en la pantalla; no viaja a la API. */
  key: string;
  part: string;
  otherText: string;
  /** Como la escribe la escuadrilla: "1,5". */
  quantity: string;
}

// Mayor que cero, con coma o punto y hasta tres decimales (como NUMERIC(12,3) en la base).
const QUANTITY = /^\d{1,9}([.,]\d{1,3})?$/;

/** La cantidad escrita ("1,5") como la espera la API ("1.5"), o null si no vale. */
export function parseQuantity(text: string): string | null {
  const clean = text.trim();
  // "1.500" puede ser mil quinientos o uno y medio: se pide con coma o sin punto.
  if (!QUANTITY.test(clean) || /\.\d{3}$/.test(clean)) {
    return null;
  }
  const value = clean.replace(",", ".");
  return Number(value) > 0 ? value : null;
}

function normalize(text: string): string {
  return text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

/** Materiales que coinciden con lo buscado, sin los que ya están cargados. */
export function matchingParts(parts: PartChoice[], search: string, used: string[]): PartChoice[] {
  const wanted = normalize(search.trim());
  return parts.filter((part) => !used.includes(part.id) && normalize(part.name).includes(wanted));
}
