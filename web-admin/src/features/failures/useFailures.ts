import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../api/client";
import { catalogSaveError } from "../catalogs/errors";
import type { Failure, FailureUpdate } from "./types";

// Prefijo común: cualquier cambio invalida todos los listados de fallas.
const FAILURES_KEY = ["failures"] as const;

/**
 * Sin tipo de equipo, la API devuelve todas las fallas; con un tipo, las suyas más las
 * genéricas (o solo las genéricas si el tipo está desactivado).
 */
export function useFailures(equipmentTypeId: string | null, includeInactive: boolean) {
  return useQuery<Failure[]>({
    queryKey: [...FAILURES_KEY, { equipmentTypeId, includeInactive }],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/failures", {
        params: {
          query: {
            include_inactive: includeInactive,
            ...(equipmentTypeId ? { equipment_type_id: equipmentTypeId } : {}),
          },
        },
      });
      if (error || !data) {
        throw new Error("no se pudieron cargar las fallas");
      }
      return data;
    },
  });
}

export function useCreateFailure() {
  const queryClient = useQueryClient();
  return useMutation<Failure, Error, { name: string; equipment_type_id: string | null }>({
    mutationFn: async (body) => {
      const { data, error, response } = await api.POST("/admin/failures", { body });
      if (error || !data) {
        throw catalogSaveError(response?.status, "no se pudo crear la falla");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: FAILURES_KEY }),
  });
}

export function useUpdateFailure(failureId: string) {
  const queryClient = useQueryClient();
  return useMutation<Failure, Error, FailureUpdate>({
    mutationFn: async (changes) => {
      const { data, error, response } = await api.PATCH("/admin/failures/{failure_id}", {
        params: { path: { failure_id: failureId } },
        body: changes,
      });
      if (error || !data) {
        throw catalogSaveError(response?.status, "no se pudo guardar la falla");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: FAILURES_KEY }),
  });
}
