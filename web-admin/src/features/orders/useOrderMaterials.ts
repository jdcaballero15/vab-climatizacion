import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../api/client";
import type { MaterialLineCreate, OrderMaterials } from "./types";
import { ORDERS_KEY, saveError } from "./useOrders";

// Bajo el prefijo de órdenes: un cambio refresca también el total del cobro en el listado.
const materialsKey = (orderId: string) => [...ORDERS_KEY, orderId, "materials"] as const;

/** Materiales de la orden con precio, subtotal y total (E05-05). Solo administración. */
export function useOrderMaterials(orderId: string) {
  return useQuery<OrderMaterials>({
    queryKey: materialsKey(orderId),
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/orders/{order_id}/materials", {
        params: { path: { order_id: orderId } },
      });
      if (error || !data) {
        throw new Error("No se pudieron cargar los materiales.");
      }
      return data;
    },
  });
}

function useMaterialsMutation<T>(
  orderId: string,
  call: (variables: T) => Promise<{ data?: OrderMaterials; error?: unknown }>,
  fallback: string,
) {
  const queryClient = useQueryClient();
  return useMutation<OrderMaterials, Error, T>({
    mutationFn: async (variables) => {
      const { data, error } = await call(variables);
      if (error || !data) {
        throw saveError(error, fallback);
      }
      return data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(materialsKey(orderId), data);
      return queryClient.invalidateQueries({ queryKey: ORDERS_KEY });
    },
  });
}

export function useAddMaterialLine(orderId: string) {
  return useMaterialsMutation<MaterialLineCreate>(
    orderId,
    (body) =>
      api.POST("/admin/orders/{order_id}/materials", {
        params: { path: { order_id: orderId } },
        body,
      }),
    "No se pudo agregar el material.",
  );
}

/** Cantidad con punto decimal, como la espera la API ("2.25"). */
export function useUpdateMaterialLine(orderId: string, lineId: string) {
  return useMaterialsMutation<string>(
    orderId,
    (quantity) =>
      api.PATCH("/admin/orders/{order_id}/materials/{line_id}", {
        params: { path: { order_id: orderId, line_id: lineId } },
        body: { quantity },
      }),
    "No se pudo corregir la cantidad.",
  );
}

export function useRemoveMaterialLine(orderId: string, lineId: string) {
  return useMaterialsMutation<void>(
    orderId,
    () =>
      api.POST("/admin/orders/{order_id}/materials/{line_id}/removal", {
        params: { path: { order_id: orderId, line_id: lineId } },
      }),
    "No se pudo sacar el material.",
  );
}

/** La línea "Otro" pasa a ser ese material de la lista. */
export function usePromoteMaterialLine(orderId: string, lineId: string) {
  return useMaterialsMutation<string>(
    orderId,
    (partId) =>
      api.POST("/admin/orders/{order_id}/materials/{line_id}/promotion", {
        params: { path: { order_id: orderId, line_id: lineId } },
        body: { part_id: partId },
      }),
    "No se pudo pasar el material a la lista.",
  );
}

export function useApproveOrder(orderId: string) {
  return useMaterialsMutation<void>(
    orderId,
    () =>
      api.POST("/admin/orders/{order_id}/approval", {
        params: { path: { order_id: orderId } },
      }),
    "No se pudo aprobar la orden.",
  );
}
