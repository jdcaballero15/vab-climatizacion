import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { onSessionExpired } from "../features/auth/session";
import { getAccessToken, setAccessToken } from "../features/auth/token";
import { api } from "./client";

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

// Normaliza las dos formas en que se llama a fetch: con un Request (cliente y reintento)
// o con (url, init) (la renovación del token).
function toRequest(input: Request | string, init?: RequestInit): Request {
  return input instanceof Request ? input : new Request(input, init);
}

beforeEach(() => {
  setAccessToken(null);
});

const renewed = { access_token: "nuevo", user: { id: "u1" } };

afterEach(() => vi.restoreAllMocks());

describe("interceptor de sesión", () => {
  // Criterio 1: ante un 401, renueva el token en segundo plano y reintenta solo.
  it("renueva el token tras un 401 y reintenta la request original", async () => {
    setAccessToken("viejo");

    const fetchMock = vi.fn(async (input: Request | string, init?: RequestInit) => {
      const request = toRequest(input, init);
      const path = new URL(request.url).pathname;
      if (path.endsWith("/auth/refresh")) {
        return json(renewed);
      }
      if (path.endsWith("/auth/me")) {
        return request.headers.get("Authorization") === "Bearer nuevo"
          ? json({ id: "u1" })
          : json({ detail: "expirado" }, 401);
      }
      return json({}, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    const { data, error } = await api.GET("/auth/me");

    expect(error).toBeUndefined();
    expect(data).toEqual({ id: "u1" });
    expect(getAccessToken()).toBe("nuevo");
  });

  // Criterio 4: si no se puede renovar (usuario dado de baja), limpia la sesión y avisa.
  it("avisa de sesión caída y limpia los tokens si el refresh falla", async () => {
    setAccessToken("viejo");
    const expirada = vi.fn();
    const quitar = onSessionExpired(expirada);

    const fetchMock = vi.fn(async (input: Request | string, init?: RequestInit) => {
      const request = toRequest(input, init);
      const path = new URL(request.url).pathname;
      if (path.endsWith("/auth/refresh")) {
        return json({ detail: "usuario inactivo" }, 401);
      }
      return json({ detail: "expirado" }, 401);
    });
    vi.stubGlobal("fetch", fetchMock);

    const { error } = await api.GET("/auth/me");

    expect(error).toBeDefined();
    expect(expirada).toHaveBeenCalledTimes(1);
    expect(getAccessToken()).toBeNull();
    quitar();
  });

  // Varias requests que reciben 401 a la vez comparten una sola renovación.
  it("renueva una sola vez ante 401 concurrentes", async () => {
    setAccessToken("viejo");
    let refreshCalls = 0;

    const fetchMock = vi.fn(async (input: Request | string, init?: RequestInit) => {
      const request = toRequest(input, init);
      const path = new URL(request.url).pathname;
      if (path.endsWith("/auth/refresh")) {
        refreshCalls += 1;
        return json(renewed);
      }
      return request.headers.get("Authorization") === "Bearer nuevo"
        ? json({})
        : json({ detail: "expirado" }, 401);
    });
    vi.stubGlobal("fetch", fetchMock);

    const [a, b] = await Promise.all([api.GET("/auth/me"), api.GET("/auth/me")]);

    expect(a.error).toBeUndefined();
    expect(b.error).toBeUndefined();
    expect(refreshCalls).toBe(1);
  });

  // E01-07: la renovación usa la cookie, sin mandar ningún token en el cuerpo.
  it("renueva con la cookie y sin cuerpo", async () => {
    setAccessToken("viejo");
    const refreshRequests: Request[] = [];

    const fetchMock = vi.fn(async (input: Request | string, init?: RequestInit) => {
      const request = toRequest(input, init);
      const path = new URL(request.url).pathname;
      if (path.endsWith("/auth/refresh")) {
        refreshRequests.push(request);
        return json(renewed);
      }
      return request.headers.get("Authorization") === "Bearer nuevo"
        ? json({})
        : json({ detail: "expirado" }, 401);
    });
    vi.stubGlobal("fetch", fetchMock);

    await api.GET("/auth/me");

    expect(refreshRequests).toHaveLength(1);
    expect(refreshRequests[0].credentials).toBe("same-origin");
    expect(await refreshRequests[0].text()).toBe("");
  });

  // Sin sesión iniciada, un 401 no dispara una renovación.
  it("sin access token no intenta renovar", async () => {
    const fetchMock = vi.fn(async () => json({ detail: "sin sesión" }, 401));
    vi.stubGlobal("fetch", fetchMock);

    const { error } = await api.GET("/auth/me");

    expect(error).toBeDefined();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
