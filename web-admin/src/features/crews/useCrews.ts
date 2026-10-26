import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../api/client";
import { NameTakenError } from "../catalogs/errors";
import type { Crew, CrewUpdate, FieldTechnician, FieldTechnicianUpdate } from "./types";

const CREWS_KEY = ["crews"] as const;
const FIELD_TECHNICIANS_KEY = ["field-technicians"] as const;

/**
 * Nombre repetido (409 *_name_already_exists) para el mensaje del catálogo; el resto
 * lleva el mensaje en español del backend si lo hay (por ejemplo, órdenes abiertas).
 */
function saveError(error: unknown, fallback: string): Error {
  const detail = (error as { detail?: { code?: unknown; message?: unknown } } | undefined)?.detail;
  if (typeof detail?.code === "string" && detail.code.endsWith("_name_already_exists")) {
    return new NameTakenError();
  }
  return new Error(typeof detail?.message === "string" ? detail.message : fallback);
}

export function useCrews(includeInactive: boolean) {
  return useQuery<Crew[]>({
    queryKey: [...CREWS_KEY, { includeInactive }],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/crews", {
        params: { query: { include_inactive: includeInactive } },
      });
      if (error || !data) {
        throw new Error("no se pudieron cargar las escuadrillas");
      }
      return data;
    },
  });
}

export function useCreateCrew() {
  const queryClient = useQueryClient();
  return useMutation<Crew, Error, string>({
    mutationFn: async (name) => {
      const { data, error } = await api.POST("/admin/crews", { body: { name } });
      if (error || !data) {
        throw saveError(error, "No se pudo crear la escuadrilla.");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CREWS_KEY }),
  });
}

export function useUpdateCrew(crewId: string) {
  const queryClient = useQueryClient();
  return useMutation<Crew, Error, CrewUpdate>({
    mutationFn: async (changes) => {
      const { data, error } = await api.PATCH("/admin/crews/{crew_id}", {
        params: { path: { crew_id: crewId } },
        body: changes,
      });
      if (error || !data) {
        throw saveError(error, "No se pudo guardar la escuadrilla.");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CREWS_KEY }),
  });
}

export function useFieldTechnicians(includeInactive: boolean) {
  return useQuery<FieldTechnician[]>({
    queryKey: [...FIELD_TECHNICIANS_KEY, { includeInactive }],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/field-technicians", {
        params: { query: { include_inactive: includeInactive } },
      });
      if (error || !data) {
        throw new Error("no se pudieron cargar los técnicos");
      }
      return data;
    },
  });
}

export function useCreateFieldTechnician() {
  const queryClient = useQueryClient();
  return useMutation<FieldTechnician, Error, string>({
    mutationFn: async (fullName) => {
      const { data, error } = await api.POST("/admin/field-technicians", {
        body: { full_name: fullName },
      });
      if (error || !data) {
        throw saveError(error, "No se pudo crear el técnico.");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: FIELD_TECHNICIANS_KEY }),
  });
}

export function useUpdateFieldTechnician(technicianId: string) {
  const queryClient = useQueryClient();
  return useMutation<FieldTechnician, Error, FieldTechnicianUpdate>({
    mutationFn: async (changes) => {
      const { data, error } = await api.PATCH("/admin/field-technicians/{technician_id}", {
        params: { path: { technician_id: technicianId } },
        body: changes,
      });
      if (error || !data) {
        throw saveError(error, "No se pudo guardar el técnico.");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: FIELD_TECHNICIANS_KEY }),
  });
}
