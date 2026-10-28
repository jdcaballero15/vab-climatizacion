import { useState } from "react";

import { notifyPasswordChangeRequired } from "../auth/session";
import type { UserAdmin } from "./types";
import { useResetPassword } from "./useUsers";

interface ResetPasswordPanelProps {
  user: UserAdmin;
  /** Es el usuario de la sesión: después hay que elegir una contraseña nueva para seguir. */
  self: boolean;
  onClose: () => void;
}

/**
 * Restablecer la contraseña (E01-05): primero se confirma; después se muestra la temporal
 * una sola vez. Al cerrar el panel se pierde: solo vivió en esta respuesta.
 */
export function ResetPasswordPanel({ user, self, onClose }: ResetPasswordPanelProps) {
  const reset = useResetPassword({ self });
  const [copied, setCopied] = useState(false);

  if (reset.data) {
    const temporary = reset.data.temporary_password;
    return (
      <div
        className="users__reset"
        role="region"
        aria-label={`Contraseña temporal de ${user.full_name}`}
      >
        <p>
          {self
            ? "Tu contraseña temporal. Anotala ahora: después no se puede volver a ver."
            : `Contraseña temporal de ${user.full_name}. Pasásela ahora: después no se puede volver a ver.`}
        </p>
        <div className="users__temporary">
          <code>{temporary}</code>
          <button
            type="button"
            className="btn--sm"
            onClick={() => {
              void navigator.clipboard.writeText(temporary).then(() => setCopied(true));
            }}
          >
            {copied ? "Copiada" : "Copiar"}
          </button>
        </div>
        <p className="muted">
          {self
            ? "Al tocar Listo te va a pedir que elijas una contraseña nueva, con esta temporal."
            : "Al entrar le va a pedir que elija una contraseña nueva."}
        </p>
        <button
          type="button"
          className="btn--primary"
          onClick={() => {
            onClose();
            if (self) {
              notifyPasswordChangeRequired();
            }
          }}
        >
          Listo
        </button>
      </div>
    );
  }

  return (
    <div
      className="users__reset"
      role="region"
      aria-label={`Restablecer la contraseña de ${user.full_name}`}
    >
      <p>
        {self
          ? "Es tu propio usuario: se genera una contraseña temporal y se cierran todas tus sesiones. Para seguir vas a tener que elegir una nueva, y la próxima vez que entres, usarla."
          : `Se genera una contraseña temporal para ${user.full_name} y se cierran todas sus sesiones abiertas, también la del celular.`}
      </p>
      {reset.isError && (
        <p className="users__error" role="alert">
          {reset.error.message}
        </p>
      )}
      <div className="users__actions">
        <button
          type="button"
          className="btn--primary"
          onClick={() => reset.mutate(user.id)}
          disabled={reset.isPending}
        >
          Confirmar restablecimiento
        </button>
        <button type="button" onClick={onClose} disabled={reset.isPending}>
          Volver
        </button>
      </div>
    </div>
  );
}
