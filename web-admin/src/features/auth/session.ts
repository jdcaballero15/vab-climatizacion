// Aviso de sesión caída: lo emite el cliente de API cuando no logra renovar el token
// (por ejemplo, un usuario dado de baja) y lo escucha AppRoot para volver al login.
type Listener = () => void;

const listeners = new Set<Listener>();

export function onSessionExpired(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function notifySessionExpired(): void {
  for (const listener of listeners) {
    listener();
  }
}

// Aviso de contraseña temporal: la API niega todo con 403 `password_change_required`
// (E01-05), por ejemplo después de restablecerse la contraseña a uno mismo. AppRoot lo
// escucha y muestra la pantalla para elegir una nueva en lugar de quedar con errores.
const passwordListeners = new Set<Listener>();

export function onPasswordChangeRequired(listener: Listener): () => void {
  passwordListeners.add(listener);
  return () => {
    passwordListeners.delete(listener);
  };
}

export function notifyPasswordChangeRequired(): void {
  for (const listener of passwordListeners) {
    listener();
  }
}
