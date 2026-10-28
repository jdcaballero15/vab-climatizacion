import { api } from "../../api/client";
import type { components } from "../../api/schema";
import { toClosurePayload } from "./closure";
import {
  deleteClosureDraft,
  saveClosureDraft,
  type ClosureProblem,
  type StoredClosure,
} from "./closureDrafts";
import { PhotoUploadError, uploadPhotos } from "./photos";

type Closure = components["schemas"]["ClosureTechnicianOut"];

/**
 * Cómo terminó un envío. `offline`: sin señal o el servidor caído, queda pendiente.
 * `rejected`: la orden ya no está en curso. `invalid`: vuelve al formulario con el campo.
 */
export type SendResult =
  | { kind: "closed"; closure: Closure }
  | { kind: "offline" }
  | { kind: "rejected"; stored: StoredClosure }
  | { kind: "invalid"; stored: StoredClosure };

export const REJECTED_MESSAGE =
  "La oficina canceló o reasignó la orden, y el cierre no se pudo enviar.";

interface ApiErrorDetail {
  code?: string;
  field?: string;
  message?: string;
}

// El formulario y el reintento pueden querer mandar el mismo cierre a la vez.
const inFlight = new Map<string, Promise<SendResult>>();

/**
 * Envía un cierre guardado (E05-13). Primero lo deja pendiente en el celular, así un
 * corte en cualquier punto lo deja listo para el reintento. Las fotos confirmadas no se
 * vuelven a subir y la clave de idempotencia (E05-12) evita duplicar el cierre.
 */
export function sendClosure(closure: StoredClosure): Promise<SendResult> {
  const key = `${closure.userId}/${closure.orderId}`;
  let sending = inFlight.get(key);
  if (!sending) {
    sending = send(closure).finally(() => inFlight.delete(key));
    inFlight.set(key, sending);
  }
  return sending;
}

async function send(start: StoredClosure): Promise<SendResult> {
  let closure: StoredClosure = { ...start, status: "pending", problem: null };
  const persist = (changes: Partial<StoredClosure>) => {
    closure = { ...closure, ...changes };
    return saveClosureDraft(closure);
  };
  const invalid = async (problem: ClosureProblem, changes: Partial<StoredClosure> = {}) => {
    await persist({ ...changes, status: "draft", problem });
    return { kind: "invalid", stored: closure } as const;
  };
  await persist({});

  let photoIds: string[];
  try {
    photoIds = await uploadPhotos(closure.photos, (photoKey, changes) => {
      void persist({
        photos: closure.photos.map((photo) =>
          photo.key === photoKey ? { ...photo, ...changes } : photo,
        ),
      });
    });
  } catch (error) {
    if (error instanceof PhotoUploadError && !error.offline) {
      return invalid({ field: "photo_ids", message: error.message });
    }
    return { kind: "offline" };
  }

  let result: Awaited<ReturnType<typeof postClosure>>;
  try {
    result = await postClosure(closure, photoIds);
  } catch {
    return { kind: "offline" };
  }
  const { data, error, response } = result;
  if (data) {
    await deleteClosureDraft(closure.userId, closure.orderId);
    return { kind: "closed", closure: data };
  }
  if (response.status === 404 || response.status === 409) {
    await persist({ status: "rejected", problem: { field: "", message: REJECTED_MESSAGE } });
    return { kind: "rejected", stored: closure };
  }
  if (response.status === 422) {
    const detail = (error as { detail?: ApiErrorDetail } | undefined)?.detail ?? {};
    const changes: Partial<StoredClosure> = {};
    if (detail.code === "idempotency_key_reused") {
      changes.idempotencyKey = crypto.randomUUID();
    }
    if (detail.field === "photo_ids") {
      // La API no acepta alguna foto: el próximo envío las sube de nuevo.
      changes.photos = closure.photos.map((photo) => ({ ...photo, fileId: null, uploaded: false }));
    }
    return invalid(
      { field: detail.field ?? "", message: detail.message ?? "Revisá los datos del cierre." },
      changes,
    );
  }
  return { kind: "offline" };
}

function postClosure(closure: StoredClosure, photoIds: string[]) {
  return api.POST("/tech/orders/{order_id}/closure", {
    params: { path: { order_id: closure.orderId } },
    body: toClosurePayload(closure.draft, closure.idempotencyKey, photoIds),
  });
}
