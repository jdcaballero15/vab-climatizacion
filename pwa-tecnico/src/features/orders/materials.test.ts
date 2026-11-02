import { describe, expect, it } from "vitest";

import { matchingParts, parseQuantity } from "./materials";

const GAS = { id: "p1", name: "Gas R410A", unit: "kg" };
const CANO = { id: "p2", name: "Caño de cobre 1/4", unit: "metro" };

describe("parseQuantity", () => {
  it("acepta coma o punto, con hasta tres decimales", () => {
    expect(parseQuantity("1,5")).toBe("1.5");
    expect(parseQuantity(" 1.5 ")).toBe("1.5");
    expect(parseQuantity("3")).toBe("3");
    expect(parseQuantity("0,125")).toBe("0.125");
  });

  it("rechaza cero, vacío, letras y más de tres decimales", () => {
    for (const text of ["0", "0,0", "", "abc", "1,2345", "-1", "1,"]) {
      expect(parseQuantity(text)).toBeNull();
    }
  });
});

describe("matchingParts", () => {
  it("busca sin acentos ni mayúsculas y saca los ya cargados", () => {
    expect(matchingParts([GAS, CANO], "cano", [])).toEqual([CANO]);
    expect(matchingParts([GAS, CANO], "", ["p1"])).toEqual([CANO]);
  });
});
