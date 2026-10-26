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
