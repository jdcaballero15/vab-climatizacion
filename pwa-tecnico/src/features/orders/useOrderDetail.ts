import { useQuery } from "@tanstack/react-query";

import { api } from "../../api/client";
import { MY_ORDERS_KEY } from "./useMyOrders";

/** Detalle de una orden de la escuadrilla. null si no está entre las suyas (404). */
export function useOrderDetail(orderId: string) {
  return useQuery({
    queryKey: [...MY_ORDERS_KEY, orderId],
    queryFn: async () => {
      const { data, error, response } = await api.GET("/tech/orders/{order_id}", {
        params: { path: { order_id: orderId } },
      });
      if (response.status === 404) {
        return null;
      }
      if (error || !data) {
        throw new Error("No se pudo cargar la orden.");
      }
      return data;
    },
    refetchOnWindowFocus: true,
  });
}
