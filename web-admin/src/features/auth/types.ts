import type { components } from "../../api/schema";

// Lo que comparten el login y la renovación. Tipos generados desde el OpenAPI del backend.
export type Session = Pick<components["schemas"]["TokenResponse"], "access_token" | "user">;
