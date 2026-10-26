import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../api/client";
import { catalogSaveError } from "../catalogs/errors";
import { REPAIRS_KEY } from "../catalogs/queryKeys";
import type { Repair, RepairCreate, RepairUpdate } from "./types";

/**
 * Sin tipo de equipo, la API devuelve todas las reparaciones; con un tipo, las suyas más las
 * genéricas. Con una falla, solo las de esa falla.
 */
export function useRepairs(
  equipmentTypeId: string | null,
  failureId: string | null,
  includeInactive: boolean,
) {
  return useQuery<Repair[]>({
    queryKey: [...REPAIRS_KEY, { equipmentTypeId, failureId, includeInactive }],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/repairs", {
        params: {
          query: {
            include_inactive: includeInactive,
            ...(equipmentTypeId ? { equipment_type_id: equipmentTypeId } : {}),
            ...(failureId ? { failure_id: failureId } : {}),
          },
        },
      });
      if (error || !data) {
        throw new Error("no se pudieron cargar las reparaciones");
      }
      return data;
    },
  });
}

export function useCreateRepair() {
  const queryClient = useQueryClient();
  return useMutation<Repair, Error, RepairCreate>({
    mutationFn: async (body) => {
      const { data, error, response } = await api.POST("/admin/repairs", { body });
      if (error || !data) {
        throw catalogSaveError(response?.status, "no se pudo crear la reparación");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: REPAIRS_KEY }),
  });
}

export function useUpdateRepair(repairId: string) {
  const queryClient = useQueryClient();
  return useMutation<Repair, Error, RepairUpdate>({
    mutationFn: async (changes) => {
      const { data, error, response } = await api.PATCH("/admin/repairs/{repair_id}", {
        params: { path: { repair_id: repairId } },
        body: changes,
      });
      if (error || !data) {
        throw catalogSaveError(response?.status, "no se pudo guardar la reparación");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: REPAIRS_KEY }),
  });
}
