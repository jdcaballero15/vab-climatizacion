import { describe, expect, it } from "vitest";

import { findSimilar, matchesSearch } from "./similar";

const CANO = { name: "Caño de Cobre 1/4" };
const GAS = { name: "Gas R410A" };

describe("findSimilar", () => {
  it("encuentra un nombre parecido sin acentos, mayúsculas ni espacios", () => {
    expect(findSimilar("cano de cobre", [GAS, CANO])).toBe(CANO);
    expect(findSimilar("gas  r410a", [GAS, CANO])).toBe(GAS);
  });

  it("no avisa si no hay nada parecido o el nombre está vacío", () => {
    expect(findSimilar("Capacitor", [GAS, CANO])).toBeNull();
    expect(findSimilar("   ", [GAS, CANO])).toBeNull();
  });
});

describe("matchesSearch", () => {
  it("busca por parte del nombre sin acentos", () => {
    expect(matchesSearch(CANO.name, "cano")).toBe(true);
    expect(matchesSearch(CANO.name, "gas")).toBe(false);
    expect(matchesSearch(CANO.name, "")).toBe(true);
  });
});
