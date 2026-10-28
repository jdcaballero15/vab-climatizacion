import type { ClosureDraft } from "./closure";

// Borrador del cierre en el celular (E05-13, ADR 0009): uno por orden y por usuario, para
// que otra escuadrilla que entre en el mismo celular no vea los ajenos.

const DB_NAME = "vab-ot";
const DB_VERSION = 1;
const STORE = "closure-drafts";
const BY_USER = "by-user";

/** Una foto del borrador: ya comprimida, con el id del archivo si llegó al bucket. */
export interface StoredPhoto {
  key: string;
  blob: Blob;
  fileId: string | null;
  uploaded: boolean;
}

export interface StoredClosure {
  userId: string;
  orderId: string;
  draft: ClosureDraft;
  idempotencyKey: string;
  photos: StoredPhoto[];
}

/**
 * Copia campo por campo lo que carga el técnico: así nunca se cuela otro dato al celular
 * (E05-13, criterio 8: nada de precios, mano de obra ni historial).
 */
function pick(closure: StoredClosure): StoredClosure {
  const { draft } = closure;
  return {
    userId: closure.userId,
    orderId: closure.orderId,
    draft: {
      technicianIds: [...draft.technicianIds],
      taskIds: [...draft.taskIds],
      outcome: draft.outcome,
      notDoneReason: draft.notDoneReason,
      failure: draft.failure,
      failureOther: draft.failureOther,
      repair: draft.repair,
      repairOther: draft.repairOther,
      equipmentCondition: draft.equipmentCondition,
      observation: draft.observation,
    },
    idempotencyKey: closure.idempotencyKey,
    photos: closure.photos.map(({ key, blob, fileId, uploaded }) => ({
      key,
      blob,
      fileId,
      uploaded,
    })),
  };
}

function request<T>(req: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function open(): Promise<IDBDatabase> | null {
  if (typeof indexedDB === "undefined") {
    return null;
  }
  const req = indexedDB.open(DB_NAME, DB_VERSION);
  req.onupgradeneeded = () => {
    const store = req.result.createObjectStore(STORE, { keyPath: ["userId", "orderId"] });
    store.createIndex(BY_USER, "userId");
  };
  return request(req);
}

// Una operación por vez y en orden: cada cambio del formulario guarda, y un guardado viejo
// no puede terminar después de uno nuevo ni del borrado al enviar.
let queue: Promise<unknown> = Promise.resolve();

/**
 * Corre `work` en una transacción y espera a que se escriba. Si el navegador no tiene
 * IndexedDB o falla, devuelve `fallback`: el cierre sigue andando, sin borrador.
 */
function withStore<T>(
  mode: IDBTransactionMode,
  fallback: T,
  work: (store: IDBObjectStore) => IDBRequest | null,
): Promise<T> {
  const run = queue.then(() => transact(mode, fallback, work));
  queue = run;
  return run;
}

async function transact<T>(
  mode: IDBTransactionMode,
  fallback: T,
  work: (store: IDBObjectStore) => IDBRequest | null,
): Promise<T> {
  try {
    const opening = open();
    if (!opening) {
      return fallback;
    }
    const db = await opening;
    try {
      const tx = db.transaction(STORE, mode);
      const req = work(tx.objectStore(STORE));
      await new Promise<void>((resolve, reject) => {
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error);
        tx.onabort = () => reject(tx.error);
      });
      return req ? (req.result as T) : fallback;
    } finally {
      db.close();
    }
  } catch {
    return fallback;
  }
}

export async function saveClosureDraft(closure: StoredClosure): Promise<void> {
  await withStore("readwrite", undefined, (store) => store.put(pick(closure)));
}

export async function loadClosureDraft(
  userId: string,
  orderId: string,
): Promise<StoredClosure | null> {
  const found = await withStore<StoredClosure | undefined>("readonly", undefined, (store) =>
    store.get([userId, orderId]),
  );
  return found ?? null;
}

export async function deleteClosureDraft(userId: string, orderId: string): Promise<void> {
  await withStore("readwrite", undefined, (store) => store.delete([userId, orderId]));
}

/** Ids de las órdenes con borrador de este usuario. */
export async function listClosureDrafts(userId: string): Promise<string[]> {
  const keys = await withStore<IDBValidKey[]>("readonly", [], (store) =>
    store.index(BY_USER).getAllKeys(IDBKeyRange.only(userId)),
  );
  return keys.map((key) => (key as [string, string])[1]);
}
