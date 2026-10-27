import { useQuery } from "@tanstack/react-query";

import { api } from "../../api/client";
import { MY_ORDERS_KEY } from "./useMyOrders";

/** Listas para cerrar la orden. null si no es una orden En curso de la escuadrilla (404). */
export function useClosureOptions(orderId: string) {
  return useQuery({
    queryKey: [...MY_ORDERS_KEY, orderId, "closure-options"],
    queryFn: async () => {
      const { data, error, response } = await api.GET("/tech/orders/{order_id}/closure-options", {
        params: { path: { order_id: orderId } },
      });
      if (response.status === 404) {
        return null;
      }
      if (error || !data) {
        throw new Error("No se pudieron cargar las listas del cierre.");
      }
      return data;
    },
  });
}
