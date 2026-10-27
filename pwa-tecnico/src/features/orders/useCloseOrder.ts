import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "../../api/client";
import type { components } from "../../api/schema";
import type { ClosureCreate } from "./closure";
import { MY_ORDERS_KEY } from "./useMyOrders";

type Closure = components["schemas"]["ClosureTechnicianOut"];

export type CloseOrderResult =
  | { kind: "closed"; closure: Closure }
  | { kind: "not_found" }
  | { kind: "invalid"; code: string; field: string; message: string };

interface ApiErrorDetail {
  code?: string;
  field?: string;
  message?: string;
}

/**
 * Envía el cierre (E05-04, E05-08). Reintentar con la misma clave de idempotencia es
 * seguro: el backend devuelve el cierre original (E05-12). Un 422 vuelve como resultado
 * con el campo, para marcarlo en el formulario.
 */
export function useCloseOrder(orderId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: ClosureCreate): Promise<CloseOrderResult> => {
      const { data, error, response } = await api.POST("/tech/orders/{order_id}/closure", {
        params: { path: { order_id: orderId } },
        body: payload,
      });
      if (response.status === 404) {
        return { kind: "not_found" };
      }
      if (response.status === 422) {
        const detail = (error as { detail?: ApiErrorDetail } | undefined)?.detail ?? {};
        return {
          kind: "invalid",
          code: detail.code ?? "invalid",
          field: detail.field ?? "",
          message: detail.message ?? "Revisá los datos del cierre.",
        };
      }
      if (error || !data) {
        throw new Error("No se pudo enviar el cierre.");
      }
      return { kind: "closed", closure: data };
    },
    onSuccess: (result) => {
      if (result.kind !== "closed") {
        return;
      }
      // La orden cerrada ya no está entre las abiertas de la escuadrilla.
      queryClient.removeQueries({ queryKey: [...MY_ORDERS_KEY, orderId] });
      void queryClient.invalidateQueries({ queryKey: MY_ORDERS_KEY, exact: true });
    },
  });
}
