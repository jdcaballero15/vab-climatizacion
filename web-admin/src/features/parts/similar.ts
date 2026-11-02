/** Minúsculas, sin acentos ni espacios: "Caño  de Cobre" y "cano de cobre" se comparan igual. */
function normalize(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/\s+/g, "");
}

/**
 * Un material ya cargado con un nombre parecido, para avisar antes de crear un duplicado
 * (E02-05, criterio 3). Es solo un aviso: se puede guardar igual.
 */
export function findSimilar<T extends { name: string }>(name: string, parts: T[]): T | null {
  const wanted = normalize(name);
  if (!wanted) {
    return null;
  }
  return (
    parts.find((part) => {
      const existing = normalize(part.name);
      return existing.includes(wanted) || wanted.includes(existing);
    }) ?? null
  );
}

export function matchesSearch(name: string, search: string): boolean {
  return normalize(name).includes(normalize(search));
}
