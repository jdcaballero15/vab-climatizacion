import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

// E12-06: la app se usa con una mano, al sol y con guantes finos. Se revisa el CSS: alto
// de lo que se toca, contraste de los textos y tamaños en rem (siguen la fuente del celular).
const css = readFileSync(resolve(__dirname, "../index.css"), "utf-8");

/** El cuerpo de la regla del selector, también si va agrupado con otros ("a,\nb {"). */
function rule(selector: string): string {
  const alone = css.indexOf(`\n${selector} {`);
  const grouped = css.indexOf(`\n${selector},`);
  const start = alone >= 0 ? alone : grouped;
  expect(start, `falta la regla ${selector}`).toBeGreaterThanOrEqual(0);
  return css.slice(css.indexOf("{", start), css.indexOf("}", start));
}

function variable(name: string): string {
  const match = css.match(new RegExp(`${name}:\\s*(#[0-9a-fA-F]{6})`));
  expect(match, `falta ${name}`).not.toBeNull();
  return match![1];
}

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const channel = parseInt(hex.slice(i, i + 2), 16) / 255;
    return channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [light, dark] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (light + 0.05) / (dark + 0.05);
}

describe("uso a la intemperie (E12-06)", () => {
  // Criterio 1: al menos 48 px de alto en lo que se toca.
  it.each([".btn-primary", ".btn-secondary", ".orders__tabs button", ".order-detail__facts a"])(
    "%s mide al menos 48 px de alto",
    (selector) => {
      const height = rule(selector).match(/min-height:\s*(\d+)px/);
      expect(height).not.toBeNull();
      expect(Number(height![1])).toBeGreaterThanOrEqual(48);
    },
  );

  // Criterio 2: contraste WCAG AA (4,5:1) de los textos sobre blanco y sobre el fondo.
  it.each(["--text", "--text-secondary", "--text-muted", "--danger", "--primary-dark"])(
    "%s cumple AA",
    (name) => {
      const color = variable(name);
      expect(contrast(color, "#ffffff")).toBeGreaterThanOrEqual(4.5);
      expect(contrast(color, variable("--bg"))).toBeGreaterThanOrEqual(4.5);
    },
  );

  // Criterio 4: los textos en rem, para que sigan la fuente agrandada del celular.
  it("no fija tamaños de letra en px", () => {
    expect(css).not.toMatch(/font-size:\s*\d+px/);
  });
});
