import createClient from "openapi-fetch";

import { getAccessToken } from "../features/auth/token";
import type { paths } from "./schema";

const baseUrl = import.meta.env.VITE_API_URL ?? "/api";

// Cliente tipado contra el OpenAPI del backend. Los tipos salen de schema.d.ts
// (generado con `npm run generate:api`), nunca escritos a mano.
// Se resuelve globalThis.fetch en cada llamada para poder mockearlo en los tests.
export const api = createClient<paths>({
  baseUrl,
  fetch: (request) => globalThis.fetch(request),
});

// Agrega el token de la sesión a cada request si hay uno.
api.use({
  onRequest({ request }) {
    const token = getAccessToken();
    if (token) {
      request.headers.set("Authorization", `Bearer ${token}`);
    }
    return request;
  },
});
