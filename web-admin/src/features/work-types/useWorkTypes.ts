import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../api/client";
import { catalogSaveError } from "../catalogs/errors";
import type { Task, TaskUpdate, WorkType, WorkTypeUpdate } from "./types";

// Prefijo común: cualquier cambio invalida tipos y subtareas, activos o no.
const WORK_TYPES_KEY = ["work-types"] as const;

export function useWorkTypes(includeInactive: boolean) {
  return useQuery<WorkType[]>({
    queryKey: [...WORK_TYPES_KEY, { includeInactive }],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/work-types", {
        params: { query: { include_inactive: includeInactive } },
      });
      if (error || !data) {
        throw new Error("no se pudieron cargar los tipos de trabajo");
      }
      return data;
    },
  });
}

export function useCreateWorkType() {
  const queryClient = useQueryClient();
  return useMutation<WorkType, Error, string>({
    mutationFn: async (name) => {
      const { data, error, response } = await api.POST("/admin/work-types", { body: { name } });
      if (error || !data) {
        throw catalogSaveError(response?.status, "no se pudo crear el tipo de trabajo");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: WORK_TYPES_KEY }),
  });
}

export function useUpdateWorkType(workTypeId: string) {
  const queryClient = useQueryClient();
  return useMutation<WorkType, Error, WorkTypeUpdate>({
    mutationFn: async (changes) => {
      const { data, error, response } = await api.PATCH("/admin/work-types/{work_type_id}", {
        params: { path: { work_type_id: workTypeId } },
        body: changes,
      });
      if (error || !data) {
        throw catalogSaveError(response?.status, "no se pudo guardar el tipo de trabajo");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: WORK_TYPES_KEY }),
  });
}

export function useTasks(workTypeId: string, includeInactive: boolean) {
  return useQuery<Task[]>({
    queryKey: [...WORK_TYPES_KEY, workTypeId, "tasks", { includeInactive }],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/work-types/{work_type_id}/tasks", {
        params: {
          path: { work_type_id: workTypeId },
          query: { include_inactive: includeInactive },
        },
      });
      if (error || !data) {
        throw new Error("no se pudieron cargar las subtareas");
      }
      return data;
    },
  });
}

export function useCreateTask(workTypeId: string) {
  const queryClient = useQueryClient();
  return useMutation<Task, Error, string>({
    mutationFn: async (name) => {
      const { data, error, response } = await api.POST("/admin/work-types/{work_type_id}/tasks", {
        params: { path: { work_type_id: workTypeId } },
        body: { name },
      });
      if (error || !data) {
        throw catalogSaveError(response?.status, "no se pudo crear la subtarea");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: WORK_TYPES_KEY }),
  });
}

export function useUpdateTask(workTypeId: string, taskId: string) {
  const queryClient = useQueryClient();
  return useMutation<Task, Error, TaskUpdate>({
    mutationFn: async (changes) => {
      const { data, error, response } = await api.PATCH(
        "/admin/work-types/{work_type_id}/tasks/{task_id}",
        { params: { path: { work_type_id: workTypeId, task_id: taskId } }, body: changes },
      );
      if (error || !data) {
        throw catalogSaveError(response?.status, "no se pudo guardar la subtarea");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: WORK_TYPES_KEY }),
  });
}
