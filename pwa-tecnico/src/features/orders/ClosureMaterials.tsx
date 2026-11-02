import { useState } from "react";

import { OTHER } from "./closure";
import { matchingParts, type MaterialDraft, type PartChoice } from "./materials";

interface ClosureMaterialsProps {
  parts: PartChoice[];
  materials: MaterialDraft[];
  onChange: (materials: MaterialDraft[]) => void;
}

/**
 * Materiales usados en la visita (E05-05): de la lista, con su unidad, o "Otro" escrito a
 * mano. Solo nombre, unidad y cantidad: la escuadrilla nunca ve precios.
 */
export function ClosureMaterials({ parts, materials, onChange }: ClosureMaterialsProps) {
  const [search, setSearch] = useState("");
  const used = materials.map((line) => line.part);
  const found = search.trim() ? matchingParts(parts, search, used) : [];
  const byId = new Map(parts.map((part) => [part.id, part]));

  const add = (part: string) => {
    onChange([...materials, { key: crypto.randomUUID(), part, otherText: "", quantity: "" }]);
    setSearch("");
  };
  const change = (key: string, changes: Partial<MaterialDraft>) =>
    onChange(materials.map((line) => (line.key === key ? { ...line, ...changes } : line)));
  const remove = (key: string) => onChange(materials.filter((line) => line.key !== key));

  return (
    <div className="closure__materials">
      {materials.length > 0 && (
        <ul className="closure__material-list">
          {materials.map((line) => {
            const part = byId.get(line.part);
            const name = part ? part.name : line.otherText.trim() || "Otro material";
            return (
              <li key={line.key} className="closure__material">
                {part ? (
                  <span className="closure__material-name">{part.name}</span>
                ) : (
                  <label className="closure__other">
                    ¿Qué material es?
                    <input
                      type="text"
                      className="closure__input"
                      maxLength={255}
                      value={line.otherText}
                      onChange={(event) => change(line.key, { otherText: event.target.value })}
                    />
                  </label>
                )}
                <div className="closure__material-qty">
                  <input
                    type="text"
                    inputMode="decimal"
                    className="closure__input"
                    aria-label={
                      part
                        ? `Cantidad de ${part.name} (${part.unit})`
                        : "Cantidad del otro material"
                    }
                    placeholder="Cantidad (ej: 1,5)"
                    value={line.quantity}
                    onChange={(event) => change(line.key, { quantity: event.target.value })}
                  />
                  {part && <span className="closure__material-unit">{part.unit}</span>}
                  <button
                    type="button"
                    className="closure__material-remove"
                    aria-label={`Quitar ${name}`}
                    onClick={() => remove(line.key)}
                  >
                    Quitar
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <input
        type="search"
        className="closure__input"
        aria-label="Buscar material"
        placeholder="Buscar material (ej: gas, caño)"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
      />
      {found.length > 0 && (
        <div className="closure__material-results">
          {found.slice(0, 8).map((part) => (
            <button
              key={part.id}
              type="button"
              className="closure__material-option"
              onClick={() => add(part.id)}
            >
              {part.name} · {part.unit}
            </button>
          ))}
        </div>
      )}
      {search.trim() && found.length === 0 && (
        <p className="closure__hint">No está en la lista: cargalo como "Otro".</p>
      )}
      <button type="button" className="closure__material-other" onClick={() => add(OTHER)}>
        Otro (no está en la lista)
      </button>
    </div>
  );
}
