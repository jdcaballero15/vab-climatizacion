import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "../../api/client";
import { getRefreshToken, setAccessToken, setRefreshToken } from "./token";

// Cierra la sesión: invalida el refresh token en el servidor y, pase lo que pase con
// esa llamada, limpia los datos locales (tokens en memoria y cache de TanStack Query).
export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, void>({
    mutationFn: async () => {
      const refreshToken = getRefreshToken();
      if (refreshToken) {
        await api.POST("/auth/logout", { body: { refresh_token: refreshToken } });
      }
    },
    onSettled: () => {
      setAccessToken(null);
      setRefreshToken(null);
      queryClient.clear();
    },
  });
}
