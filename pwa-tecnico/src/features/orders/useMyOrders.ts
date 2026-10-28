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

// Aparte de MY_ORDERS_KEY: las claves que empiezan con esa son de una orden abierta.
export const DONE_ORDERS_KEY = ["tech", "done"] as const;

/** Cierres de la escuadrilla en los últimos 7 días (E05-14). */
export function useDoneOrders() {
  return useQuery({
    queryKey: DONE_ORDERS_KEY,
    queryFn: async () => {
      const { data, error } = await api.GET("/tech/orders/done");
      if (error || !data) {
        throw new Error("No se pudieron cargar las órdenes hechas.");
      }
      return data;
    },
    refetchOnWindowFocus: true,
  });
}

/**
 * Una orden recién cerrada ya no está entre las abiertas de la escuadrilla, y su cierre
 * pasa a las hechas de la semana.
 */
export function forgetClosedOrder(queryClient: QueryClient, orderId: string) {
  queryClient.removeQueries({ queryKey: [...MY_ORDERS_KEY, orderId] });
  void queryClient.invalidateQueries({ queryKey: MY_ORDERS_KEY, exact: true });
  void queryClient.invalidateQueries({ queryKey: DONE_ORDERS_KEY });
}
