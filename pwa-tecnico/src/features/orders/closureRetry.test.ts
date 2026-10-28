import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { memory, saveClosureDraft, storedFor } from "../../test/memoryClosureDrafts";
import { EMPTY_DRAFT } from "./closure";
import type { ClosureState, StoredClosure } from "./closureDrafts";
import { retryDelay, schedulePendingClosures, startClosureRetry } from "./closureRetry";

vi.mock("./closureDrafts", () => import("../../test/memoryClosureDrafts"));

const USER = "90000000-0000-4000-8000-000000000001";

function stored(orderId: string, status: ClosureState): StoredClosure {
  return {
    userId: USER,
    orderId,
    status,
    problem: null,
    order: null,
    draft: {
      ...EMPTY_DRAFT,
      technicianIds: ["a1"],
      outcome: "done",
      equipmentCondition: "working",
    },
    idempotencyKey: `clave-${orderId}`,
    photos: [],
    signature: null,
  };
}

const CLOSED = {
  id: "e1",
  outcome: "done",
  order_status: "done",
  closed_at: "2026-10-28T12:00:00Z",
};

let online = false;
let posts: string[];

function stubApi() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (request: Request) => {
      posts.push(new URL(request.url).pathname.split("/").at(-2)!);
      if (!online) {
        throw new TypeError("Failed to fetch");
      }
      return new Response(JSON.stringify(CLOSED), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
}

/** Deja correr las promesas pendientes y avanza el reloj. */
const advance = (ms: number) => vi.advanceTimersByTimeAsync(ms);

let stop: () => void = () => {};

beforeEach(() => {
  vi.useFakeTimers();
  memory.clear();
  online = false;
  posts = [];
  stubApi();
});

afterEach(() => {
  stop();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("retryDelay", () => {
  it("espera cada vez más, hasta 5 minutos", () => {
    expect([0, 1, 2, 3].map(retryDelay)).toEqual([5_000, 10_000, 20_000, 40_000]);
    expect(retryDelay(20)).toBe(300_000);
  });
});

describe("startClosureRetry", () => {
  // E05-13, criterio 3: al abrir la app con señal se mandan los pendientes.
  it("al abrir manda los pendientes del usuario y no los borradores ni los rechazados", async () => {
    online = true;
    await saveClosureDraft(stored("o1", "pending"));
    await saveClosureDraft(stored("o2", "draft"));
    await saveClosureDraft(stored("o3", "rejected"));
    await saveClosureDraft({ ...stored("o4", "pending"), userId: "otro-usuario" });
    const onClosed = vi.fn();

    stop = startClosureRetry(USER, onClosed);
    await advance(0);

    expect(posts).toEqual(["o1"]);
    expect(onClosed).toHaveBeenCalledWith("o1");
    expect(storedFor(USER, "o1")).toBeUndefined();
    expect(storedFor(USER, "o2")?.status).toBe("draft");
  });

  // Criterio 3 y notas técnicas: sin señal reintenta con espera creciente.
  it("sin señal reintenta con espera creciente hasta que sale", async () => {
    await saveClosureDraft(stored("o1", "pending"));

    stop = startClosureRetry(USER, () => {});
    await advance(0);
    expect(posts).toHaveLength(1);

    await advance(4_999);
    expect(posts).toHaveLength(1);
    await advance(1);
    expect(posts).toHaveLength(2);

    await advance(9_999);
    expect(posts).toHaveLength(2);
    online = true;
    await advance(1);
    expect(posts).toHaveLength(3);
    expect(storedFor(USER, "o1")).toBeUndefined();

    await advance(600_000);
    expect(posts).toHaveLength(3);
  });

  it("al volver la señal reintenta en el momento", async () => {
    await saveClosureDraft(stored("o1", "pending"));
    stop = startClosureRetry(USER, () => {});
    await advance(0);

    online = true;
    window.dispatchEvent(new Event("online"));
    await advance(0);

    expect(posts).toHaveLength(2);
    expect(storedFor(USER, "o1")).toBeUndefined();
  });

  it("un cierre que queda pendiente después de abrir entra en el reintento", async () => {
    stop = startClosureRetry(USER, () => {});
    await advance(0);
    expect(posts).toHaveLength(0);

    await saveClosureDraft(stored("o1", "pending"));
    schedulePendingClosures();
    online = true;
    await advance(5_000);

    expect(posts).toEqual(["o1"]);
  });

  it("al cerrar sesión deja de reintentar", async () => {
    await saveClosureDraft(stored("o1", "pending"));
    stop = startClosureRetry(USER, () => {});
    await advance(0);

    stop();
    online = true;
    window.dispatchEvent(new Event("online"));
    await advance(600_000);

    expect(posts).toHaveLength(1);
  });
});
