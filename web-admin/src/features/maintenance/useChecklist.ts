import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../api/client";
import { catalogSaveError } from "../catalogs/errors";
import type { CheckStep, CheckStepUpdate } from "./types";

const STEPS_KEY = ["maintenance-check-steps"] as const;

/** Pasos del checklist único de mantenimiento, en orden (E07-01). */
export function useCheckSteps(includeInactive: boolean) {
  return useQuery<CheckStep[]>({
    queryKey: [...STEPS_KEY, { includeInactive }],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/maintenance/check-steps", {
        params: { query: { include_inactive: includeInactive } },
      });
      if (error || !data) {
        throw new Error("no se pudo cargar el checklist");
      }
      return data;
    },
  });
}

export function useCreateCheckStep() {
  const queryClient = useQueryClient();
  return useMutation<CheckStep, Error, string>({
    mutationFn: async (name) => {
      const { data, error, response } = await api.POST("/admin/maintenance/check-steps", {
        body: { name },
      });
      if (error || !data) {
        throw catalogSaveError(response?.status, "no se pudo agregar el paso");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: STEPS_KEY }),
  });
}

export function useUpdateCheckStep(stepId: string) {
  const queryClient = useQueryClient();
  return useMutation<CheckStep, Error, CheckStepUpdate>({
    mutationFn: async (body) => {
      const { data, error, response } = await api.PATCH(
        "/admin/maintenance/check-steps/{step_id}",
        { params: { path: { step_id: stepId } }, body },
      );
      if (error || !data) {
        throw catalogSaveError(response?.status, "no se pudo guardar el paso");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: STEPS_KEY }),
  });
}

/** El orden nuevo de los pasos activos: todos, como se ven en la lista. */
export function useReorderCheckSteps() {
  const queryClient = useQueryClient();
  return useMutation<CheckStep[], Error, string[]>({
    mutationFn: async (stepIds) => {
      const { data, error } = await api.PUT("/admin/maintenance/check-steps/order", {
        body: { step_ids: stepIds },
      });
      if (error || !data) {
        const detail = (error as { detail?: { message?: unknown } } | undefined)?.detail;
        throw new Error(
          typeof detail?.message === "string" ? detail.message : "No se pudo cambiar el orden.",
        );
      }
      return data;
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: STEPS_KEY }),
  });
}
