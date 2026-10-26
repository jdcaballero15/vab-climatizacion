import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../api/client";
import type { ClientSummary } from "../clients/types";
import type {
  Assignment,
  AssignmentCreate,
  PendingOrderPage,
  WorkOrder,
  WorkOrderCreate,
} from "./types";

const ORDERS_KEY = ["orders"] as const;
export const PAGE_SIZE = 50;
// Desde este largo la búsqueda del backend compara por contención (ver /admin/clients/similar).
export const MIN_CLIENT_SEARCH = 4;

/** Error con el mensaje en español que manda el backend ({code, message}), si lo hay. */
function saveError(error: unknown, fallback: string): Error {
  const detail = (error as { detail?: { message?: unknown } } | undefined)?.detail;
  return new Error(typeof detail?.message === "string" ? detail.message : fallback);
}

export function usePendingOrders(offset: number) {
  return useQuery<PendingOrderPage>({
    queryKey: [...ORDERS_KEY, "pending", { offset }],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/orders", {
        params: { query: { status: "pending", limit: PAGE_SIZE, offset } },
      });
      if (error || !data) {
        throw new Error("no se pudieron cargar las órdenes pendientes");
      }
      return data;
    },
    placeholderData: keepPreviousData,
  });
}

export function useCreateOrder() {
  const queryClient = useQueryClient();
  return useMutation<WorkOrder, Error, WorkOrderCreate>({
    mutationFn: async (nueva) => {
      const { data, error } = await api.POST("/admin/orders", { body: nueva });
      if (error || !data) {
        throw saveError(error, "No se pudo crear la orden.");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ORDERS_KEY }),
  });
}

export function useAssignOrder(orderId: string) {
  const queryClient = useQueryClient();
  return useMutation<Assignment, Error, AssignmentCreate>({
    mutationFn: async (asignacion) => {
      const { data, error } = await api.POST("/admin/orders/{order_id}/assignment", {
        params: { path: { order_id: orderId } },
        body: asignacion,
      });
      if (error || !data) {
        throw saveError(error, "No se pudo asignar la orden.");
      }
      return data;
    },
    // La orden deja de estar pendiente: se refresca el listado.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ORDERS_KEY }),
  });
}

/** Clientes cuyo nombre contiene el texto, sin distinguir mayúsculas ni acentos. */
export function useClientSearch(text: string) {
  const name = text.trim();
  return useQuery<ClientSummary[]>({
    queryKey: ["clients", "search", name],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/clients/similar", {
        params: { query: { name } },
      });
      if (error || !data) {
        throw new Error("no se pudieron buscar los clientes");
      }
      return data;
    },
    enabled: name.length >= MIN_CLIENT_SEARCH,
    placeholderData: keepPreviousData,
  });
}
