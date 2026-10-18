import createClient from "openapi-fetch";

import type { paths } from "./schema";

const baseUrl = import.meta.env.VITE_API_URL ?? "/api";

// Cliente tipado contra el OpenAPI del backend. El tecnico solo usa rutas /tech/.
// Los tipos salen de schema.d.ts (generado con `npm run generate:api`).
export const api = createClient<paths>({ baseUrl });
