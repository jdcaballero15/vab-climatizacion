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
        throw new Error("login_failed");
      }
      return data;
    },
  });
}
