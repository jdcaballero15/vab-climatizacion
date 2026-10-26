import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "../../api/client";
import { MY_ORDERS_KEY } from "./useMyOrders";

/**
 * Inicia la orden (Asignada -> En curso). Deja el detalle actualizado en la caché y
 * vuelve a pedir la lista. Si ya no es de la escuadrilla (404), el detalle pasa a null.
 * Es idempotente en el backend, así que reintentar es seguro.
 */
export function useStartOrder(orderId: string) {
  const queryClient = useQueryClient();
  const detailKey = [...MY_ORDERS_KEY, orderId];

  return useMutation({
    mutationFn: async () => {
      const { data, error, response } = await api.POST("/tech/orders/{order_id}/start", {
        params: { path: { order_id: orderId } },
      });
      if (response.status === 404) {
        return null;
      }
      if (error || !data) {
        throw new Error("No se pudo iniciar la orden.");
      }
      return data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(detailKey, data);
      void queryClient.invalidateQueries({ queryKey: MY_ORDERS_KEY, exact: true });
    },
  });
}
