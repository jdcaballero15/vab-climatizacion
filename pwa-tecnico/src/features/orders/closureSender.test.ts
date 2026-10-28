import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { memory, storedFor } from "../../test/memoryClosureDrafts";
import { EMPTY_DRAFT } from "./closure";
import type { StoredClosure } from "./closureDrafts";
import { REJECTED_MESSAGE, sendClosure } from "./closureSender";

vi.mock("./closureDrafts", () => import("../../test/memoryClosureDrafts"));

const USER = "90000000-0000-4000-8000-000000000001";
const ORDER = "6f1c2a9e-0000-4000-8000-000000000001";
const KEY = "7c000000-0000-4000-8000-000000000001";
const BUCKET = "https://bucket.example";

function stored(overrides: Partial<StoredClosure> = {}): StoredClosure {
  return {
    userId: USER,
    orderId: ORDER,
    status: "draft",
    problem: null,
    order: { number: 5, workTypeName: "Reparación", clientName: "Sanatorio Ficticio" },
    draft: {
      ...EMPTY_DRAFT,
      technicianIds: ["a0000000-0000-4000-8000-000000000001"],
      outcome: "done",
      equipmentCondition: "working",
    },
    idempotencyKey: KEY,
    photos: [1, 2].map((n) => ({
      key: `foto-${n}`,
      blob: new Blob([`foto ${n}`], { type: "image/jpeg" }),
      fileId: null,
      uploaded: false,
    })),
    ...overrides,
  };
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const CLOSED = {
  id: "e0000000-0000-4000-8000-000000000001",
  outcome: "done",
  order_status: "done",
  closed_at: "2026-10-28T12:00:00Z",
};

let calls: string[];
let sent: { idempotency_key: string; photo_ids: string[] }[];

/**
 * Simula archivos, bucket y cierre. `closure` responde el cierre; `put` puede cortar la
 * subida al bucket de la foto n (empieza en 1).
 */
function stubApi(
  closure: () => Response = () => json(CLOSED, 201),
  put: (n: number) => Response = () => new Response(null, { status: 200 }),
) {
  let files = 0;
  let puts = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (target: Request | string, init?: RequestInit) => {
      const input = target instanceof Request ? target : new Request(target, init);
      const path = new URL(input.url).pathname;
      if (input.url.startsWith(BUCKET)) {
        calls.push("PUT bucket");
        return put(++puts);
      }
      if (path.endsWith("/confirm")) {
        calls.push("confirm");
        return json({ id: path.split("/").at(-2) });
      }
      if (path.endsWith("/files")) {
        calls.push("POST files");
        const id = `f0000000-0000-4000-8000-00000000000${++files}`;
        return json({ file_id: id, upload_url: `${BUCKET}/${id}`, expires_in: 300 }, 201);
      }
      calls.push("POST closure");
      sent.push((await input.json()) as (typeof sent)[number]);
      return closure();
    }),
  );
}

const offline = () => {
  throw new TypeError("Failed to fetch");
};

beforeEach(() => {
  memory.clear();
  calls = [];
  sent = [];
});

afterEach(() => vi.restoreAllMocks());

describe("sendClosure", () => {
  // E05-13, criterio 5.
  it("sube las fotos, envía el cierre y borra lo guardado", async () => {
    stubApi();

    const result = await sendClosure(stored());

    expect(result).toMatchObject({ kind: "closed", closure: { order_status: "done" } });
    expect(calls).toEqual([
      "POST files",
      "PUT bucket",
      "confirm",
      "POST files",
      "PUT bucket",
      "confirm",
      "POST closure",
    ]);
    expect(sent[0]).toMatchObject({
      idempotency_key: KEY,
      photo_ids: ["f0000000-0000-4000-8000-000000000001", "f0000000-0000-4000-8000-000000000002"],
    });
    expect(storedFor(USER, ORDER)).toBeUndefined();
  });

  // Criterio 3: sin señal queda pendiente para el reintento.
  it("sin señal deja el cierre pendiente", async () => {
    stubApi(offline);

    expect(await sendClosure(stored())).toEqual({ kind: "offline" });
    expect(storedFor(USER, ORDER)?.status).toBe("pending");
  });

  it("si el servidor falla también queda pendiente", async () => {
    stubApi(() => json({ detail: "Internal Server Error" }, 500));

    expect(await sendClosure(stored())).toEqual({ kind: "offline" });
    expect(storedFor(USER, ORDER)?.status).toBe("pending");
  });

  // Criterio 4: cortado a mitad, el reintento no duplica fotos y usa la misma clave.
  it("cortado en la segunda foto, el reintento sigue desde ahí con la misma clave", async () => {
    stubApi(undefined, (n) => (n === 2 ? offline() : new Response(null, { status: 200 })));

    expect(await sendClosure(stored())).toEqual({ kind: "offline" });
    const pending = storedFor(USER, ORDER)!;
    expect(pending.photos.map((photo) => photo.uploaded)).toEqual([true, false]);

    calls = [];
    stubApi();
    expect((await sendClosure(pending)).kind).toBe("closed");
    expect(calls).toEqual(["POST files", "PUT bucket", "confirm", "POST closure"]);
    expect(sent[0].idempotency_key).toBe(KEY);
  });

  it("si el cierre llegó pero no la respuesta, el reintento no resube las fotos", async () => {
    stubApi(offline);
    await sendClosure(stored());

    calls = [];
    stubApi(() => json(CLOSED, 200));
    expect((await sendClosure(storedFor(USER, ORDER)!)).kind).toBe("closed");
    expect(calls).toEqual(["POST closure"]);
  });

  // Criterio 6: la oficina canceló o reasignó.
  it.each([404, 409])("con %i lo marca rechazado y no lo borra", async (status) => {
    stubApi(() =>
      json({ detail: { code: "order_not_found", message: "No se encontró." } }, status),
    );

    const result = await sendClosure(stored());

    expect(result.kind).toBe("rejected");
    expect(storedFor(USER, ORDER)).toMatchObject({
      status: "rejected",
      problem: { field: "", message: REJECTED_MESSAGE },
    });
  });

  // Criterio 7: un error de validación vuelve al formulario con el campo.
  it("con 422 vuelve a borrador con el campo marcado", async () => {
    stubApi(() =>
      json(
        { detail: { code: "invalid", field: "observation", message: "Escribí qué falta." } },
        422,
      ),
    );

    const result = await sendClosure(stored());

    expect(result.kind).toBe("invalid");
    expect(storedFor(USER, ORDER)).toMatchObject({
      status: "draft",
      problem: { field: "observation", message: "Escribí qué falta." },
      idempotencyKey: KEY,
    });
  });

  it("una clave usada en otra orden se cambia por una nueva", async () => {
    stubApi(() =>
      json(
        {
          detail: { code: "idempotency_key_reused", field: "idempotency_key", message: "Clave." },
        },
        422,
      ),
    );

    await sendClosure(stored());

    expect(storedFor(USER, ORDER)?.idempotencyKey).not.toBe(KEY);
  });

  it("si la API no acepta las fotos, quedan para subirse de nuevo", async () => {
    stubApi(() =>
      json({ detail: { code: "invalid", field: "photo_ids", message: "Foto inválida." } }, 422),
    );

    await sendClosure(stored());

    expect(storedFor(USER, ORDER)?.photos.map((photo) => photo.fileId)).toEqual([null, null]);
  });

  it("dos envíos a la vez del mismo cierre mandan uno solo", async () => {
    stubApi();

    const [first, second] = await Promise.all([sendClosure(stored()), sendClosure(stored())]);

    expect(first).toBe(second);
    expect(calls.filter((call) => call === "POST closure")).toHaveLength(1);
  });
});
