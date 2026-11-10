import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api } from "../../api/client";
import type { components } from "../../api/schema";

export type Dashboard = components["schemas"]["DashboardOut"];

/** Los filtros del tablero, tal cual viajan en la URL (E10-08, criterio 3). */
export interface DashboardFilters {
  date_from?: string;
  date_to?: string;
  client_id?: string;
  crew_id?: string;
  work_type_id?: string;
  equipment_type_id?: string;
  compare_from?: string;
  compare_to?: string;
}

export function useDashboard(filters: DashboardFilters) {
  return useQuery<Dashboard>({
    queryKey: ["dashboard", filters],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/dashboard", {
        params: { query: filters },
      });
      if (error || !data) {
        throw new Error("no se pudo cargar el tablero");
      }
      return data;
    },
    placeholderData: keepPreviousData,
  });
}
