// Reemplazo en memoria de closureDrafts.ts para los tests de pantallas y del envío.
// IndexedDB se prueba en closureDrafts.test.ts.
import type { StoredClosure } from "../features/orders/closureDrafts";

export const memory = new Map<string, StoredClosure>();
const listeners = new Set<() => void>();

const keyOf = (userId: string, orderId: string) => `${userId}/${orderId}`;

// Copia como IndexedDB, pero sin clonar los Blob (el clon pierde el de jsdom).
function copy(closure: StoredClosure): StoredClosure {
  return {
    ...closure,
    problem: closure.problem && { ...closure.problem },
    order: closure.order && { ...closure.order },
    draft: { ...closure.draft },
    photos: closure.photos.map((photo) => ({ ...photo })),
    signature: closure.signature ? { ...closure.signature } : null,
  };
}

export function storedFor(userId: string, orderId: string) {
  return memory.get(keyOf(userId, orderId));
}

export async function saveClosureDraft(closure: StoredClosure) {
  memory.set(keyOf(closure.userId, closure.orderId), copy(closure));
  listeners.forEach((listener) => listener());
}

export async function loadClosureDraft(userId: string, orderId: string) {
  const found = memory.get(keyOf(userId, orderId));
  return found ? copy(found) : null;
}

export async function deleteClosureDraft(userId: string, orderId: string) {
  memory.delete(keyOf(userId, orderId));
  listeners.forEach((listener) => listener());
}

export async function listStoredClosures(userId: string) {
  return [...memory.values()]
    .filter((closure) => closure.userId === userId)
    .map((closure) => copy(closure));
}

export function onClosureDraftsChanged(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
