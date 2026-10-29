import {
  keepPreviousData,
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api } from "../../api/client";
import type { ClientSummary } from "../clients/types";
import type {
  Assignment,
  AssignmentCreate,
  UnassignmentCreate,
  Cancellation,
  CancellationCreate,
  ClosureDetail,
  ListableStatus,
  OrderListPage,
  EquipmentChange,
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

export function useOrderList(status: ListableStatus, offset: number) {
  return useQuery<OrderListPage>({
    queryKey: [...ORDERS_KEY, status, { offset }],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/orders", {
        params: { query: { status, limit: PAGE_SIZE, offset } },
      });
      if (error || !data) {
        throw new Error("no se pudieron cargar las órdenes");
      }
      return data;
    },
    placeholderData: keepPreviousData,
  });
}

/** Cuántas órdenes hay en cada estado: el total de una página de una sola orden. */
export function useOrderCounts(statuses: ListableStatus[]) {
  const results = useQueries({
    queries: statuses.map((status) => ({
      queryKey: [...ORDERS_KEY, status, "count"],
      queryFn: async () => {
        const { data, error } = await api.GET("/admin/orders", {
          params: { query: { status, limit: 1, offset: 0 } },
        });
        if (error || !data) {
          throw new Error("no se pudo contar las órdenes");
        }
        return data.total;
      },
    })),
  });
  return Object.fromEntries(
    statuses.map((status, index) => [status, results[index]?.data]),
  ) as Partial<Record<ListableStatus, number>>;
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

/** Agrega, cambia o saca el equipo de una orden Pendiente o Asignada (E04-12). */
export function useChangeEquipment(orderId: string) {
  const queryClient = useQueryClient();
  return useMutation<WorkOrder, Error, EquipmentChange>({
    mutationFn: async (cambio) => {
      const { data, error } = await api.PUT("/admin/orders/{order_id}/equipment", {
        params: { path: { order_id: orderId } },
        body: cambio,
      });
      if (error || !data) {
        throw saveError(error, "No se pudo cambiar el equipo.");
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

/** Otra escuadrilla o fecha para una orden Asignada o En curso (E04-04). */
export function useReassignOrder(orderId: string) {
  const queryClient = useQueryClient();
  return useMutation<Assignment, Error, AssignmentCreate>({
    mutationFn: async (asignacion) => {
      const { data, error } = await api.POST("/admin/orders/{order_id}/reassignment", {
        params: { path: { order_id: orderId } },
        body: asignacion,
      });
      if (error || !data) {
        throw saveError(error, "No se pudo reasignar la orden.");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ORDERS_KEY }),
  });
}

/** Devuelve una orden Asignada a Pendientes (E04-04). */
export function useUnassignOrder(orderId: string) {
  const queryClient = useQueryClient();
  return useMutation<void, Error, UnassignmentCreate>({
    mutationFn: async (desasignacion) => {
      const { error } = await api.POST("/admin/orders/{order_id}/unassignment", {
        params: { path: { order_id: orderId } },
        body: desasignacion,
      });
      if (error) {
        throw saveError(error, "No se pudo desasignar la orden.");
      }
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ORDERS_KEY }),
  });
}

export function useCancelOrder(orderId: string) {
  const queryClient = useQueryClient();
  return useMutation<Cancellation, Error, CancellationCreate>({
    mutationFn: async (cancelacion) => {
      const { data, error } = await api.POST("/admin/orders/{order_id}/cancellation", {
        params: { path: { order_id: orderId } },
        body: cancelacion,
      });
      if (error || !data) {
        throw saveError(error, "No se pudo cancelar la orden.");
      }
      return data;
    },
    // La orden pasa a Canceladas: se refrescan todos los listados.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ORDERS_KEY }),
  });
}

const PHOTO_URL_REFRESH_MS = 4 * 60 * 1000;

/** Lo que cargó la escuadrilla en el último cierre (E04-08, criterio 1). */
export function useOrderClosure(orderId: string) {
  return useQuery<ClosureDetail>({
    queryKey: [...ORDERS_KEY, orderId, "closure"],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/orders/{order_id}/closure", {
        params: { path: { order_id: orderId } },
      });
      if (error || !data) {
        throw new Error("no se pudo cargar el cierre");
      }
      return data;
    },
    // Las URLs de las fotos vencen a los 5 minutos (E00-09): se renuevan antes.
    staleTime: PHOTO_URL_REFRESH_MS,
    refetchInterval: PHOTO_URL_REFRESH_MS,
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
