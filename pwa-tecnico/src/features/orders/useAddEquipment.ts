import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../api/client";
import type { components } from "../../api/schema";
import { MY_ORDERS_KEY } from "./useMyOrders";

export type NewEquipment = components["schemas"]["EquipmentTechnicianCreate"];

/** Tipos de equipo activos, para elegir al cargar uno (E05-15). */
export function useEquipmentTypes(enabled: boolean) {
  return useQuery({
    queryKey: ["tech", "equipment-types"],
    enabled,
    staleTime: 10 * 60 * 1000,
    queryFn: async () => {
      const { data, error } = await api.GET("/tech/equipment-types");
      if (error || !data) {
        throw new Error("No se pudieron cargar los tipos de equipo.");
      }
      return data;
    },
  });
}

/** Error con el mensaje del backend (422 o 409) o, si no hay respuesta, el de conexión. */
export class AddEquipmentError extends Error {}

/**
 * Carga el equipo de una orden que no tiene (E05-15). Deja el detalle actualizado en la
 * caché y vuelve a pedir la lista, que también muestra el equipo.
 */
export function useAddEquipment(orderId: string) {
  const queryClient = useQueryClient();
  const detailKey = [...MY_ORDERS_KEY, orderId];

  return useMutation({
    mutationFn: async (body: NewEquipment) => {
      let result;
      try {
        result = await api.POST("/tech/orders/{order_id}/equipment", {
          params: { path: { order_id: orderId } },
          body,
        });
      } catch {
        throw new AddEquipmentError("No hay conexión. Probá de nuevo cuando tengas señal.");
      }
      const { data, error } = result;
      if (error || !data) {
        const detail = (error as { detail?: { message?: string } } | undefined)?.detail;
        throw new AddEquipmentError(
          detail?.message ?? "No se pudo guardar el equipo. Revisá los datos.",
        );
      }
      return data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(detailKey, data);
      void queryClient.invalidateQueries({ queryKey: MY_ORDERS_KEY, exact: true });
    },
  });
}
