import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../api/client";
import { ORDERS_KEY } from "../orders/useOrders";
import type {
  MaintenancePlan,
  MaintenancePlanCreate,
  MaintenancePlanUpdate,
  MaintenanceRun,
} from "./types";

const PLANS_KEY = ["maintenance-plans"] as const;

function saveError(error: unknown, fallback: string): Error {
  const detail = (error as { detail?: { message?: unknown } } | undefined)?.detail;
  return new Error(typeof detail?.message === "string" ? detail.message : fallback);
}

/** Planes de mantenimiento, por próxima visita; con los terminados si se piden (E07-03). */
export function usePlans(includeEnded: boolean) {
  return useQuery<MaintenancePlan[]>({
    queryKey: [...PLANS_KEY, { includeEnded }],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/maintenance/plans", {
        params: { query: { include_ended: includeEnded } },
      });
      if (error || !data) {
        throw new Error("no se pudieron cargar los planes");
      }
      return data;
    },
  });
}

export function useCreatePlan() {
  const queryClient = useQueryClient();
  return useMutation<MaintenancePlan, Error, MaintenancePlanCreate>({
    mutationFn: async (body) => {
      const { data, error } = await api.POST("/admin/maintenance/plans", { body });
      if (error || !data) {
        throw saveError(error, "No se pudo crear el plan.");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PLANS_KEY }),
  });
}

export function useUpdatePlan(planId: string) {
  const queryClient = useQueryClient();
  return useMutation<MaintenancePlan, Error, MaintenancePlanUpdate>({
    mutationFn: async (body) => {
      const { data, error } = await api.PATCH("/admin/maintenance/plans/{plan_id}", {
        params: { path: { plan_id: planId } },
        body,
      });
      if (error || !data) {
        throw saveError(error, "No se pudo guardar el plan.");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PLANS_KEY }),
  });
}

/** "Generar ahora": la misma corrida del cron de cada mañana (E07-04). */
export function useRunMaintenance() {
  const queryClient = useQueryClient();
  return useMutation<MaintenanceRun, Error, void>({
    mutationFn: async () => {
      const { data, error } = await api.POST("/admin/maintenance/run");
      if (error || !data) {
        throw new Error("No se pudieron generar las órdenes.");
      }
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PLANS_KEY });
      void queryClient.invalidateQueries({ queryKey: ORDERS_KEY });
    },
  });
}
