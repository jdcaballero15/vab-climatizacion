import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../api/client";
import { catalogSaveError } from "../catalogs/errors";
import type { EquipmentType, EquipmentTypeUpdate } from "./types";

// Prefijo común: cualquier cambio invalida los listados, activos o no.
const EQUIPMENT_TYPES_KEY = ["equipment-types"] as const;

export function useEquipmentTypes(includeInactive: boolean) {
  return useQuery<EquipmentType[]>({
    queryKey: [...EQUIPMENT_TYPES_KEY, { includeInactive }],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/equipment-types", {
        params: { query: { include_inactive: includeInactive } },
      });
      if (error || !data) {
        throw new Error("no se pudieron cargar los tipos de equipo");
      }
      return data;
    },
  });
}

export function useCreateEquipmentType() {
  const queryClient = useQueryClient();
  return useMutation<EquipmentType, Error, string>({
    mutationFn: async (name) => {
      const { data, error, response } = await api.POST("/admin/equipment-types", {
        body: { name },
      });
      if (error || !data) {
        throw catalogSaveError(response?.status, "no se pudo crear el tipo de equipo");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: EQUIPMENT_TYPES_KEY }),
  });
}

export function useUpdateEquipmentType(equipmentTypeId: string) {
  const queryClient = useQueryClient();
  return useMutation<EquipmentType, Error, EquipmentTypeUpdate>({
    mutationFn: async (changes) => {
      const { data, error, response } = await api.PATCH(
        "/admin/equipment-types/{equipment_type_id}",
        { params: { path: { equipment_type_id: equipmentTypeId } }, body: changes },
      );
      if (error || !data) {
        throw catalogSaveError(response?.status, "no se pudo guardar el tipo de equipo");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: EQUIPMENT_TYPES_KEY }),
  });
}
