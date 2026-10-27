import createClient from "openapi-fetch";

import { notifySessionExpired } from "../features/auth/session";
import { getAccessToken, setAccessToken } from "../features/auth/token";
import type { Session } from "../features/auth/types";
import type { paths } from "./schema";

// En los sitios desplegados y en local la API está en /api del mismo sitio (Render o
// Vite la reenvían): así la cookie del refresh token es del mismo sitio (ADR 0010).
const baseUrl = import.meta.env.VITE_API_URL ?? "/api";

// Cliente tipado contra el OpenAPI del backend. El tecnico solo usa rutas /tech/.
// Los tipos salen de schema.d.ts (generado con `npm run generate:api`).
// Se resuelve globalThis.fetch en cada llamada para poder mockearlo en los tests.
export const api = createClient<paths>({
  baseUrl,
  fetch: (request) => globalThis.fetch(request),
});

// Rutas de sesión que no deben disparar el reintento con refresh (evita bucles).
const AUTH_PATHS = ["/auth/login", "/auth/refresh", "/auth/logout"];

// Un único refresh en vuelo: varias requests que reciben 401 a la vez (o los dos montajes
// de StrictMode al abrir) comparten la misma renovación. Pedir dos con la misma cookie
// haría fallar la segunda, porque cada renovación revoca el token anterior.
let refreshInFlight: Promise<Session | null> | null = null;

async function requestRefresh(): Promise<Session | null> {
  try {
    const response = await globalThis.fetch(`${baseUrl}/auth/refresh`, {
      method: "POST",
      credentials: "same-origin",
    });
    if (!response.ok) {
      return null;
    }
    const data = (await response.json()) as Session;
    setAccessToken(data.access_token);
    return data;
  } catch {
    return null;
  }
}

/** Renueva la sesión con la cookie. Devuelve la sesión, o null si no hay una válida. */
export function refreshSession(): Promise<Session | null> {
  refreshInFlight ??= requestRefresh().finally(() => {
    refreshInFlight = null;
  });
  return refreshInFlight;
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
    if (AUTH_PATHS.some((authPath) => path.endsWith(authPath)) || !getAccessToken()) {
      return undefined;
    }

    const renovada = await refreshSession();
    if (!renovada) {
      setAccessToken(null);
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
