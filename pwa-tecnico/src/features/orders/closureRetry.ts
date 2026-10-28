import { listStoredClosures } from "./closureDrafts";
import { sendClosure } from "./closureSender";

// Reintento de los cierres pendientes mientras la app está abierta (E05-13, criterio 3):
// al abrir, al volver la señal y con espera creciente. Sin la app abierta no se envía
// nada (Background Sync quedó fuera de alcance).

const FIRST_DELAY = 5_000;
const MAX_DELAY = 5 * 60_000;

/** Espera antes del reintento número `attempt` (empieza en 0): 5 s, 10 s, 20 s... hasta 5 min. */
export function retryDelay(attempt: number): number {
  return Math.min(FIRST_DELAY * 2 ** attempt, MAX_DELAY);
}

interface Retry {
  userId: string;
  onClosed: (orderId: string) => void;
  attempt: number;
  timer: ReturnType<typeof setTimeout> | undefined;
  running: boolean;
  again: boolean;
}

let current: Retry | null = null;

/** Empieza a reintentar los pendientes de este usuario. Devuelve cómo pararlo. */
export function startClosureRetry(userId: string, onClosed: (orderId: string) => void): () => void {
  const retry: Retry = {
    userId,
    onClosed,
    attempt: 0,
    timer: undefined,
    running: false,
    again: false,
  };
  current = retry;
  const onOnline = () => {
    retry.attempt = 0;
    void run(retry);
  };
  window.addEventListener("online", onOnline);
  void run(retry);
  return () => {
    window.removeEventListener("online", onOnline);
    clearTimeout(retry.timer);
    if (current === retry) {
      current = null;
    }
  };
}

/** Un cierre acaba de quedar pendiente: entra en la espera del reintento. */
export function schedulePendingClosures(): void {
  if (!current) {
    return;
  }
  if (current.running) {
    current.again = true;
  } else if (current.timer === undefined) {
    schedule(current);
  }
}

function schedule(retry: Retry) {
  retry.timer = setTimeout(() => void run(retry), retryDelay(retry.attempt));
  retry.attempt += 1;
}

async function run(retry: Retry): Promise<void> {
  if (retry.running) {
    retry.again = true;
    return;
  }
  clearTimeout(retry.timer);
  retry.timer = undefined;
  retry.running = true;
  let offline = false;
  try {
    const pending = (await listStoredClosures(retry.userId)).filter(
      (closure) => closure.status === "pending",
    );
    for (const closure of pending) {
      if (current !== retry) {
        return;
      }
      const result = await sendClosure(closure);
      if (result.kind === "offline") {
        offline = true;
        break;
      }
      if (result.kind === "closed") {
        retry.onClosed(closure.orderId);
      }
    }
  } finally {
    retry.running = false;
  }
  if (current !== retry) {
    return;
  }
  if (retry.again) {
    retry.again = false;
    return run(retry);
  }
  if (offline) {
    schedule(retry);
  } else {
    retry.attempt = 0;
  }
}
