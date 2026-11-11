import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../api/client";
import type {
  AdjustmentCreate,
  LocationCreate,
  LocationUpdate,
  Movement,
  MovementPage,
  ReceiptCreate,
  StockLocation,
  StockPart,
  TransferCreate,
} from "./types";

export const STOCK_KEY = ["stock"] as const;

function saveError(error: unknown, fallback: string): Error {
  const detail = (error as { detail?: { message?: unknown } } | undefined)?.detail;
  return new Error(typeof detail?.message === "string" ? detail.message : fallback);
}

export function useLocations(includeInactive: boolean) {
  return useQuery<StockLocation[]>({
    queryKey: [...STOCK_KEY, "locations", { includeInactive }],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/stock/locations", {
        params: { query: { include_inactive: includeInactive } },
      });
      if (error || !data) {
        throw new Error("no se pudieron cargar las ubicaciones");
      }
      return data;
    },
  });
}

export function useStock(filters: { partId?: string; locationId?: string }) {
  return useQuery<StockPart[]>({
    queryKey: [...STOCK_KEY, "balance", filters],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/stock", {
        params: {
          query: {
            part_id: filters.partId || undefined,
            location_id: filters.locationId || undefined,
          },
        },
      });
      if (error || !data) {
        throw new Error("no se pudo cargar el stock");
      }
      return data;
    },
  });
}

export const MOVEMENTS_PAGE = 50;

/** Una página del historial del repuesto, el más nuevo primero (E08-07). */
export function useMovements(partId: string | null, offset: number) {
  return useQuery<MovementPage>({
    queryKey: [...STOCK_KEY, "movements", partId, offset],
    enabled: partId !== null,
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/stock/parts/{part_id}/movements", {
        params: { path: { part_id: partId ?? "" }, query: { limit: MOVEMENTS_PAGE, offset } },
      });
      if (error || !data) {
        throw new Error("no se pudo cargar el historial");
      }
      return data;
    },
  });
}

export function useSaveLocation(locationId?: string) {
  const queryClient = useQueryClient();
  return useMutation<StockLocation, Error, LocationCreate | LocationUpdate>({
    mutationFn: async (body) => {
      const { data, error } = locationId
        ? await api.PATCH("/admin/stock/locations/{location_id}", {
            params: { path: { location_id: locationId } },
            body: body as LocationUpdate,
          })
        : await api.POST("/admin/stock/locations", { body: body as LocationCreate });
      if (error || !data) {
        throw saveError(error, "No se pudo guardar la ubicación.");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: STOCK_KEY }),
  });
}

export type MovementRequest =
  | { kind: "receipt"; body: ReceiptCreate }
  | { kind: "transfer"; body: TransferCreate }
  | { kind: "adjustment"; body: AdjustmentCreate };

/** Ingreso (E08-02), transferencia (E08-03) o ajuste con motivo (E08-06). */
export function useMovement() {
  const queryClient = useQueryClient();
  return useMutation<Movement, Error, MovementRequest>({
    mutationFn: async (request) => {
      const { data, error } =
        request.kind === "receipt"
          ? await api.POST("/admin/stock/receipts", { body: request.body })
          : request.kind === "transfer"
            ? await api.POST("/admin/stock/transfers", { body: request.body })
            : await api.POST("/admin/stock/adjustments", { body: request.body });
      if (error || !data) {
        throw saveError(error, "No se pudo registrar el movimiento.");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: STOCK_KEY }),
  });
}
