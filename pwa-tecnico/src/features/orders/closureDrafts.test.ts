// @vitest-environment node
// Con el Blob de jsdom el clon de fake-indexeddb pierde el contenido; el de Node no.
import "fake-indexeddb/auto";
import { IDBFactory } from "fake-indexeddb";
import { beforeEach, describe, expect, it } from "vitest";

import { EMPTY_DRAFT } from "./closure";
import {
  deleteClosureDraft,
  listStoredClosures,
  loadClosureDraft,
  onClosureDraftsChanged,
  saveClosureDraft,
  type StoredClosure,
} from "./closureDrafts";

const CELULAR1 = "u0000000-0000-4000-8000-000000000001";
const CELULAR2 = "u0000000-0000-4000-8000-000000000002";
const ORDER = "o0000000-0000-4000-8000-000000000001";
const OTHER_ORDER = "o0000000-0000-4000-8000-000000000002";

function stored(overrides: Partial<StoredClosure> = {}): StoredClosure {
  return {
    userId: CELULAR1,
    orderId: ORDER,
    status: "draft",
    problem: null,
    order: { number: 5, workTypeName: "Reparación", clientName: "Sanatorio Ficticio" },
    draft: { ...EMPTY_DRAFT, technicianIds: ["ana"], observation: "Filtro sucio" },
    idempotencyKey: "clave-1",
    photos: [
      {
        key: "foto-1",
        blob: new Blob(["foto"], { type: "image/jpeg" }),
        fileId: null,
        uploaded: false,
      },
    ],
    ...overrides,
  };
}

/** Órdenes con cierre guardado de un usuario. */
async function orderIds(userId: string) {
  return (await listStoredClosures(userId)).map((closure) => closure.orderId).sort();
}

beforeEach(() => {
  // Una base vacía por test.
  globalThis.indexedDB = new IDBFactory();
});

describe("closureDrafts", () => {
  // E05-13, criterios 1 y 2: lo guardado vuelve igual al abrir de nuevo.
  it("guarda el borrador de una orden y lo devuelve", async () => {
    await saveClosureDraft(stored());

    const loaded = await loadClosureDraft(CELULAR1, ORDER);

    expect(loaded?.draft).toEqual(stored().draft);
    expect(loaded?.idempotencyKey).toBe("clave-1");
    expect(loaded?.photos).toHaveLength(1);
    expect(loaded?.photos[0]).toMatchObject({ key: "foto-1", fileId: null, uploaded: false });
    expect(loaded?.photos[0].blob.size).toBe(4);
  });

  it("guardar de nuevo reemplaza el borrador de esa orden", async () => {
    await saveClosureDraft(stored());
    await saveClosureDraft(
      stored({ draft: { ...EMPTY_DRAFT, observation: "Cambio" }, photos: [] }),
    );

    const loaded = await loadClosureDraft(CELULAR1, ORDER);

    expect(loaded?.draft.observation).toBe("Cambio");
    expect(loaded?.photos).toEqual([]);
    expect(await orderIds(CELULAR1)).toEqual([ORDER]);
  });

  it("sin borrador devuelve null", async () => {
    expect(await loadClosureDraft(CELULAR1, ORDER)).toBeNull();
  });

  // Notas técnicas: otro usuario en el mismo celular no ve borradores ajenos.
  it("cada usuario ve solo sus borradores", async () => {
    await saveClosureDraft(stored());
    await saveClosureDraft(stored({ orderId: OTHER_ORDER }));

    expect(await loadClosureDraft(CELULAR2, ORDER)).toBeNull();
    expect(await orderIds(CELULAR2)).toEqual([]);
    expect(await orderIds(CELULAR1)).toEqual([ORDER, OTHER_ORDER]);
  });

  it("borra el borrador de una orden sin tocar los demás", async () => {
    await saveClosureDraft(stored());
    await saveClosureDraft(stored({ orderId: OTHER_ORDER }));
    await saveClosureDraft(stored({ userId: CELULAR2 }));

    await deleteClosureDraft(CELULAR1, ORDER);

    expect(await loadClosureDraft(CELULAR1, ORDER)).toBeNull();
    expect(await orderIds(CELULAR1)).toEqual([OTHER_ORDER]);
    expect(await orderIds(CELULAR2)).toEqual([ORDER]);
  });

  // Criterio 8: solo lo que carga el técnico. Nada de precios, mano de obra ni historial.
  it("guarda solo los campos del cierre aunque reciba otros", async () => {
    const extra = {
      ...stored(),
      price: 1000,
      labor: 500,
      history: ["Orden N° 1"],
      order: { ...stored().order, address: "Calle 1", price: 1000 },
      draft: { ...stored().draft, price: 1000 },
      photos: [{ ...stored().photos[0], previewUrl: "blob:preview" }],
    } as unknown as StoredClosure;
    await saveClosureDraft(extra);

    const loaded = await loadClosureDraft(CELULAR1, ORDER);

    expect(Object.keys(loaded ?? {}).sort()).toEqual(
      [
        "draft",
        "idempotencyKey",
        "order",
        "orderId",
        "photos",
        "problem",
        "status",
        "userId",
      ].sort(),
    );
    expect(Object.keys(loaded?.draft ?? {}).sort()).toEqual(Object.keys(EMPTY_DRAFT).sort());
    expect(loaded?.order).toEqual(stored().order);
    expect(Object.keys(loaded?.photos[0] ?? {}).sort()).toEqual(
      ["blob", "fileId", "key", "uploaded"].sort(),
    );
  });

  // Sin IndexedDB (navegación privada, celular viejo) el cierre sigue andando, sin borrador.
  it("sin IndexedDB no guarda ni falla", async () => {
    // @ts-expect-error: se simula un navegador sin IndexedDB.
    delete globalThis.indexedDB;

    await expect(saveClosureDraft(stored())).resolves.toBeUndefined();
    expect(await loadClosureDraft(CELULAR1, ORDER)).toBeNull();
    expect(await orderIds(CELULAR1)).toEqual([]);
    await expect(deleteClosureDraft(CELULAR1, ORDER)).resolves.toBeUndefined();
  });

  // Criterios 3 y 6: el estado y el motivo viajan con el cierre.
  it("guarda el estado y el problema, y los lista con todo", async () => {
    await saveClosureDraft(
      stored({ status: "rejected", problem: { field: "", message: "Ya no está en curso." } }),
    );

    const [listed] = await listStoredClosures(CELULAR1);

    expect(listed).toMatchObject({
      status: "rejected",
      problem: { field: "", message: "Ya no está en curso." },
      order: { number: 5 },
    });
  });

  it("avisa cuando se guarda o se borra un cierre", async () => {
    let changes = 0;
    const stop = onClosureDraftsChanged(() => changes++);

    await saveClosureDraft(stored());
    await deleteClosureDraft(CELULAR1, ORDER);
    stop();
    await saveClosureDraft(stored());

    expect(changes).toBe(2);
  });
});
