import createClient from "openapi-fetch";

import type { paths } from "./schema";

const baseUrl = import.meta.env.VITE_API_URL ?? "/api";

// Cliente tipado contra el OpenAPI del backend. El tecnico solo usa rutas /tech/.
// Los tipos salen de schema.d.ts (generado con `npm run generate:api`).
// Se resuelve globalThis.fetch en cada llamada para poder mockearlo en los tests.
export const api = createClient<paths>({
  baseUrl,
  fetch: (request) => globalThis.fetch(request),
});
