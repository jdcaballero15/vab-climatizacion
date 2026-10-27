import { useEffect, useState } from "react";

// Temporal: para elegir la dirección visual con el cliente. Se saca al decidir.
const THEMES = [
  { id: "sobrio", label: "Sobrio" },
  { id: "grafito", label: "Grafito" },
  { id: "hielo", label: "Hielo" },
  { id: "vidrio", label: "Vidrio" },
] as const;
const STORAGE_KEY = "ot-tema";

function savedTheme(): string {
  try {
    return localStorage.getItem(STORAGE_KEY) ?? "sobrio";
  } catch {
    return "sobrio";
  }
}

export function ThemePicker() {
  const [theme, setTheme] = useState(savedTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // Sin almacenamiento, el tema dura lo que la pestaña.
    }
  }, [theme]);

  return (
    <div className="theme-picker" role="group" aria-label="Probar estilos">
      {THEMES.map(({ id, label }) => (
        <button
          key={id}
          type="button"
          className={
            id === theme ? "theme-picker__item theme-picker__item--active" : "theme-picker__item"
          }
          aria-pressed={id === theme}
          onClick={() => setTheme(id)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
