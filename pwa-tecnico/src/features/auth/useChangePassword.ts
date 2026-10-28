import { useMutation } from "@tanstack/react-query";

import { api } from "../../api/client";
import type { Session } from "./types";

export interface PasswordChange {
  current_password: string;
  new_password: string;
}

const MESSAGES: Record<string, string> = {
  invalid_current_password: "La contraseña temporal no es correcta.",
  password_unchanged: "Tiene que ser distinta de la temporal.",
};

/** Cambia la contraseña propia (E01-05). Devuelve el usuario ya sin la marca de temporal. */
export function useChangePassword() {
  return useMutation<Session["user"], Error, PasswordChange>({
    mutationFn: async (body) => {
      const { data, error } = await api.POST("/auth/password", { body });
      if (error || !data) {
        const code = (error as { detail?: { code?: unknown } } | undefined)?.detail?.code;
        const message = typeof code === "string" ? MESSAGES[code] : undefined;
        throw new Error(message ?? "No se pudo guardar la contraseña. Probá de nuevo.");
      }
      return data;
    },
  });
}
