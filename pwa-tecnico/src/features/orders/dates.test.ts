import { describe, expect, it } from "vitest";

import { isOverdue, relativeDay } from "./dates";

describe("relativeDay", () => {
  it("nombra hoy, mañana y ayer", () => {
    expect(relativeDay("2026-10-26", "2026-10-26")).toBe("Hoy");
    expect(relativeDay("2026-10-27", "2026-10-26")).toBe("Mañana");
    expect(relativeDay("2026-10-25", "2026-10-26")).toBe("Ayer");
  });

  it("cruza meses y años", () => {
    expect(relativeDay("2026-11-01", "2026-10-31")).toBe("Mañana");
    expect(relativeDay("2026-12-31", "2027-01-01")).toBe("Ayer");
  });

  it("muestra la fecha si está más lejos", () => {
    expect(relativeDay("2026-10-29", "2026-10-26")).toBe("29/10/2026");
  });
});

describe("isOverdue", () => {
  it("solo si la fecha prevista es anterior a hoy", () => {
    expect(isOverdue("2026-10-25", "2026-10-26")).toBe(true);
    expect(isOverdue("2026-10-26", "2026-10-26")).toBe(false);
    expect(isOverdue("2026-10-27", "2026-10-26")).toBe(false);
  });
});
