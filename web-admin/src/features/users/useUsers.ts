import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../api/client";
import type { PasswordReset, UserAdmin, UserCreate } from "./types";

const USERS_KEY = ["users"] as const;

export function useUsers() {
  return useQuery<UserAdmin[]>({
    queryKey: USERS_KEY,
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/users");
      if (error || !data) {
        throw new Error("no se pudieron cargar los usuarios");
      }
      return data;
    },
  });
}

export class EmailAlreadyExistsError extends Error {}

export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation<UserAdmin, Error, UserCreate>({
    mutationFn: async (nuevo) => {
      const { data, error, response } = await api.POST("/admin/users", { body: nuevo });
      if (error || !data) {
        if (response?.status === 409) {
          throw new EmailAlreadyExistsError();
        }
        throw new Error("no se pudo crear el usuario");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: USERS_KEY }),
  });
}

export function useDeactivateUser() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (userId) => {
      const { error } = await api.DELETE("/admin/users/{user_id}", {
        params: { path: { user_id: userId } },
      });
      if (error) {
        throw new Error("no se pudo dar de baja el usuario");
      }
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: USERS_KEY }),
  });
}

/** Restablece la contraseña (E01-05): la temporal llega solo en esta respuesta. */
export function useResetPassword() {
  const queryClient = useQueryClient();
  return useMutation<PasswordReset, Error, string>({
    mutationFn: async (userId) => {
      const { data, error } = await api.POST("/admin/users/{user_id}/password-reset", {
        params: { path: { user_id: userId } },
      });
      if (error || !data) {
        throw new Error("No se pudo restablecer la contraseña. Probá de nuevo.");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: USERS_KEY }),
  });
}
