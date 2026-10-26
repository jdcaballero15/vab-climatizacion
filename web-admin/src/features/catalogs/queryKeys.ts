// Prefijos de caché de los catálogos que dependen de otros: cualquier cambio en un tipo de
// equipo o en una falla puede cambiar qué fallas o reparaciones se ofrecen.
export const FAILURES_KEY = ["failures"] as const;
export const REPAIRS_KEY = ["repairs"] as const;
