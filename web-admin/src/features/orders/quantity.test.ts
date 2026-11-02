import { describe, expect, it } from "vitest";

import { formatQuantity, toQuantity } from "./labels";

describe("cantidades de materiales", () => {
  it("se muestran con coma y sin separador de miles", () => {
    expect(formatQuantity("1.500")).toBe("1,5");
    expect(formatQuantity("1500.000")).toBe("1500");
  });

  it("lo mostrado vuelve igual al guardar", () => {
    expect(toQuantity(formatQuantity("1500.000"))).toBe("1500");
    expect(toQuantity(formatQuantity("2.250"))).toBe("2.25");
  });

  it("rechaza cero, letras y más de tres decimales", () => {
    for (const text of ["0", "abc", "1,2345", ""]) {
      expect(toQuantity(text)).toBeNull();
    }
  });
});
