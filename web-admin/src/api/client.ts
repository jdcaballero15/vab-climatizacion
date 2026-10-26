import createClient from "openapi-fetch";

import { notifySessionExpired } from "../features/auth/session";
import {
  getAccessToken,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
} from "../features/auth/token";
import type { paths } from "./schema";

const baseUrl = import.meta.env.VITE_API_URL ?? "/api";

// Cliente tipado contra el OpenAPI del backend. Los tipos salen de schema.d.ts
// (generado con `npm run generate:api`), nunca escritos a mano.
// Se resuelve globalThis.fetch en cada llamada para poder mockearlo en los tests.
export const api = createClient<paths>({
  baseUrl,
  fetch: (request) => globalThis.fetch(request),
});

// Rutas de sesión que no deben disparar el reintento con refresh (evita bucles).
const AUTH_PATHS = ["/auth/login", "/auth/refresh", "/auth/logout"];

// Un único refresh en vuelo: varias requests que reciben 401 a la vez comparten
// la misma renovación en lugar de pedir una cada una.
let refreshInFlight: Promise<boolean> | null = null;

async function refreshSession(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    return false;
  }
  const response = await globalThis.fetch(`${baseUrl}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) {
    return false;
  }
  const data = (await response.json()) as { access_token: string; refresh_token: string };
  setAccessToken(data.access_token);
  setRefreshToken(data.refresh_token);
  return true;
}

api.use({
  onRequest({ request }) {
    const token = getAccessToken();
    if (token) {
      request.headers.set("Authorization", `Bearer ${token}`);
    }
    return request;
  },
  // Renueva el token en segundo plano ante un 401 y reintenta la request original.
  // Si no se puede renovar (refresh vencido o usuario dado de baja), limpia la sesión.
  async onResponse({ request, response }) {
    if (response.status !== 401) {
      return undefined;
    }
    const path = new URL(request.url).pathname;
    if (AUTH_PATHS.some((authPath) => path.endsWith(authPath)) || !getRefreshToken()) {
      return undefined;
    }

    refreshInFlight ??= refreshSession().finally(() => {
      refreshInFlight = null;
    });
    const renovado = await refreshInFlight;
    if (!renovado) {
      setAccessToken(null);
      setRefreshToken(null);
      notifySessionExpired();
      return undefined;
    }

    try {
      const headers = new Headers(request.headers);
      headers.set("Authorization", `Bearer ${getAccessToken()}`);
      return await globalThis.fetch(new Request(request, { headers }));
    } catch {
      // El cuerpo ya se consumió y no se puede reintentar (p. ej. un POST): se
      // devuelve el 401 original; el token ya quedó renovado para la próxima acción.
      return undefined;
    }
  },
});
