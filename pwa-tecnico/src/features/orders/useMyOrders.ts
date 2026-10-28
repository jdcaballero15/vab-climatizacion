import { useQuery, type QueryClient } from "@tanstack/react-query";

import { api } from "../../api/client";

export const MY_ORDERS_KEY = ["tech", "orders"] as const;

export function useMyOrders() {
  return useQuery({
    queryKey: MY_ORDERS_KEY,
    queryFn: async () => {
      const { data, error } = await api.GET("/tech/orders");
      if (error || !data) {
        throw new Error("No se pudieron cargar las órdenes.");
      }
      return data;
    },
    // Al volver a la app, la lista se actualiza sola (criterio 4).
    refetchOnWindowFocus: true,
  });
}

/** Una orden recién cerrada ya no está entre las abiertas de la escuadrilla. */
export function forgetClosedOrder(queryClient: QueryClient, orderId: string) {
  queryClient.removeQueries({ queryKey: [...MY_ORDERS_KEY, orderId] });
  void queryClient.invalidateQueries({ queryKey: MY_ORDERS_KEY, exact: true });
}
