import { useMutation } from "@tanstack/react-query";

import { api } from "../../api/client";
import type { Session } from "./types";

export interface LoginCredentials {
  email: string;
  password: string;
}

export function useLogin() {
  return useMutation<Session, Error, LoginCredentials>({
    mutationFn: async ({ email, password }) => {
      const { data, error } = await api.POST("/auth/login", {
        body: { email, password },
      });
      if (error || !data) {
        // Con la cuenta bloqueada por intentos fallidos (E01-06), el mensaje de la API.
        const detail = (error as { detail?: { code?: unknown; message?: unknown } } | undefined)
          ?.detail;
        throw new Error(
          detail?.code === "account_locked" || detail?.code === "too_many_attempts"
            ? String(detail.message)
            : "login_failed",
        );
      }
      return data;
    },
  });
}
