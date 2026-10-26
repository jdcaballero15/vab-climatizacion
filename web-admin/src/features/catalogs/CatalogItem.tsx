import { useState, type FormEvent, type ReactNode } from "react";

import { NameTakenError } from "./errors";

interface CatalogItemProps {
  name: string;
  isActive: boolean;
  isPending: boolean;
  error: Error | null;
  /** Mensaje para un nombre que ya existe (409). */
  nameTakenMessage: string;
  onSave: (changes: { name?: string; is_active?: boolean }) => void;
  children?: ReactNode;
}

/** Fila de un catálogo: nombre, renombrar y desactivar o reactivar. Nunca se borra. */
export function CatalogItem({
  name,
  isActive,
  isPending,
  error,
  nameTakenMessage,
  onSave,
  children,
}: CatalogItemProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(name);

  function handleRename(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSave({ name: draft });
    setEditing(false);
  }

  return (
    <li className="catalog__item">
      <div className="catalog__row">
        {editing ? (
          <form
            className="catalog__rename"
            onSubmit={handleRename}
            aria-label={`Renombrar ${name}`}
          >
            <input
              aria-label="Nombre nuevo"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              required
            />
            <button type="submit" disabled={isPending}>
              Guardar
            </button>
            <button type="button" onClick={() => setEditing(false)}>
              Cancelar
            </button>
          </form>
        ) : (
          <>
            <span className={isActive ? undefined : "catalog__inactive"}>{name}</span>
            {!isActive && <span className="catalog__badge">Desactivado</span>}
            <button
              type="button"
              aria-label={`Renombrar ${name}`}
              onClick={() => {
                setDraft(name);
                setEditing(true);
              }}
            >
              Renombrar
            </button>
            <button
              type="button"
              aria-label={`${isActive ? "Desactivar" : "Reactivar"} ${name}`}
              onClick={() => onSave({ is_active: !isActive })}
              disabled={isPending}
            >
              {isActive ? "Desactivar" : "Reactivar"}
            </button>
          </>
        )}
      </div>

      {error && (
        <p className="catalog__error" role="alert">
          {error instanceof NameTakenError ? nameTakenMessage : "No se pudo guardar el cambio."}
        </p>
      )}

      {children}
    </li>
  );
}
