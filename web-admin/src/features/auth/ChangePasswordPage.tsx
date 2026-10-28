import { useState, type FormEvent } from "react";

import type { Session } from "./types";
import { useChangePassword } from "./useChangePassword";

interface ChangePasswordPageProps {
  user: Session["user"];
  onChanged: (user: Session["user"]) => void;
  onLogout: () => void;
}

const MIN_LENGTH = 8;

function validate(current: string, next: string, repeated: string): string | null {
  if (next.length < MIN_LENGTH) {
    return `Tiene que tener al menos ${MIN_LENGTH} caracteres.`;
  }
  if (next === current) {
    return "Tiene que ser distinta de la temporal.";
  }
  if (next !== repeated) {
    return "Las dos contraseñas no coinciden.";
  }
  return null;
}

/**
 * Con una contraseña temporal (E01-05) la API niega todo lo demás: antes de seguir hay que
 * elegir una nueva. Las reglas se validan acá y también en el servidor.
 */
export function ChangePasswordPage({ user, onChanged, onLogout }: ChangePasswordPageProps) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeated, setRepeated] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const change = useChangePassword();

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const found = validate(current, next, repeated);
    setProblem(found);
    if (found) {
      return;
    }
    change.mutate({ current_password: current, new_password: next }, { onSuccess: onChanged });
  }

  const message = problem ?? (change.isError ? change.error.message : null);

  return (
    <main className="login">
      <form className="login__form" onSubmit={handleSubmit} aria-label="Elegir contraseña nueva">
        <span className="login__mark" aria-hidden="true">
          OT
        </span>
        <h1 className="login__title">Elegí una contraseña nueva</h1>
        <p className="login__subtitle">
          {user.full_name}, te restablecieron la contraseña. Para seguir, elegí una que solo sepas
          vos.
        </p>

        <label htmlFor="current_password">Contraseña temporal</label>
        <input
          id="current_password"
          type="password"
          autoComplete="current-password"
          value={current}
          onChange={(event) => setCurrent(event.target.value)}
          required
        />

        <label htmlFor="new_password">Contraseña nueva</label>
        <input
          id="new_password"
          type="password"
          autoComplete="new-password"
          value={next}
          onChange={(event) => setNext(event.target.value)}
          required
        />

        <label htmlFor="repeat_password">Repetir la contraseña nueva</label>
        <input
          id="repeat_password"
          type="password"
          autoComplete="new-password"
          value={repeated}
          onChange={(event) => setRepeated(event.target.value)}
          required
        />

        {message && (
          <p className="login__error" role="alert">
            {message}
          </p>
        )}

        <button type="submit" disabled={change.isPending}>
          {change.isPending ? "Guardando…" : "Guardar y entrar"}
        </button>
        <button type="button" className="btn--ghost" onClick={onLogout}>
          Cerrar sesión
        </button>
      </form>
    </main>
  );
}
