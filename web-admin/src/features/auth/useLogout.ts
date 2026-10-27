import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "../../api/client";
import { setAccessToken } from "./token";

// Cierra la sesión: el servidor revoca el refresh token de la cookie y la borra. Pase lo
// que pase con esa llamada, se limpian los datos locales (token y cache de TanStack Query).
export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, void>({
    mutationFn: async () => {
      await api.POST("/auth/logout");
    },
    onSettled: () => {
      setAccessToken(null);
      queryClient.clear();
    },
  });
}
