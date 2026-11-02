import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../api/client";
import { catalogSaveError } from "../catalogs/errors";
import type { Part, PartCreate, PartUpdate } from "./types";

// Prefijo común: cualquier cambio invalida la lista, activos o no.
export const PARTS_KEY = ["parts"] as const;

export function useParts(includeInactive: boolean) {
  return useQuery<Part[]>({
    queryKey: [...PARTS_KEY, { includeInactive }],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/parts", {
        params: { query: { include_inactive: includeInactive } },
      });
      if (error || !data) {
        throw new Error("no se pudieron cargar los materiales");
      }
      return data;
    },
  });
}

export function useCreatePart() {
  const queryClient = useQueryClient();
  return useMutation<Part, Error, PartCreate>({
    mutationFn: async (body) => {
      const { data, error, response } = await api.POST("/admin/parts", { body });
      if (error || !data) {
        throw catalogSaveError(response?.status, "no se pudo crear el material");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PARTS_KEY }),
  });
}

export function useUpdatePart(partId: string) {
  const queryClient = useQueryClient();
  return useMutation<Part, Error, PartUpdate>({
    mutationFn: async (changes) => {
      const { data, error, response } = await api.PATCH("/admin/parts/{part_id}", {
        params: { path: { part_id: partId } },
        body: changes,
      });
      if (error || !data) {
        throw catalogSaveError(response?.status, "no se pudo guardar el material");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PARTS_KEY }),
  });
}

/** Precio con punto decimal, como lo espera la API ("1800.5"). */
export function useSetPartPrice(partId: string) {
  const queryClient = useQueryClient();
  return useMutation<Part, Error, string>({
    mutationFn: async (listPrice) => {
      const { data, error } = await api.PUT("/admin/parts/{part_id}/price", {
        params: { path: { part_id: partId } },
        body: { list_price: listPrice },
      });
      if (error || !data) {
        throw new Error("no se pudo guardar el precio");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PARTS_KEY }),
  });
}
