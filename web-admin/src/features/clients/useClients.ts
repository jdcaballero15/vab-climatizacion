import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../api/client";
import { ORDERS_KEY } from "../orders/useOrders";
import type {
  AuditEntry,
  Client,
  ClientCreate,
  ClientOrderPage,
  ClientPage,
  ClientSegment,
  ClientSummary,
  ClientUpdate,
  Contact,
  ContactCreate,
  ContactUpdate,
  Equipment,
  EquipmentCreate,
  EquipmentFile,
  EquipmentUpdate,
  MergePreview,
  SearchResults,
  Site,
  SiteCreate,
  SiteUpdate,
} from "./types";

// Prefijo común: cualquier alta o edición invalida listados y fichas.
const CLIENTS_KEY = ["clients"] as const;
export const PAGE_SIZE = 50;

/** Error con el mensaje en español que manda el backend ({code, message}), si lo hay. */
function saveError(error: unknown, fallback: string): Error {
  const detail = (error as { detail?: { message?: unknown } } | undefined)?.detail;
  return new Error(typeof detail?.message === "string" ? detail.message : fallback);
}

/** Con deleted, los dados de baja, para restaurarlos (E03-07). */
export function useClientPage(segment: ClientSegment | null, offset: number, deleted = false) {
  return useQuery<ClientPage>({
    queryKey: [...CLIENTS_KEY, "page", { segment, offset, deleted }],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/clients", {
        params: { query: { segment, limit: PAGE_SIZE, offset, deleted } },
      });
      if (error || !data) {
        throw new Error("no se pudieron cargar los clientes");
      }
      return data;
    },
    // Mantiene la página anterior a la vista mientras carga la siguiente.
    placeholderData: keepPreviousData,
  });
}

export function useClient(clientId: string) {
  return useQuery<Client>({
    queryKey: [...CLIENTS_KEY, "detail", clientId],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/clients/{client_id}", {
        params: { path: { client_id: clientId } },
      });
      if (error || !data) {
        throw new Error("no se pudo cargar el cliente");
      }
      return data;
    },
  });
}

/** Clientes con un nombre muy parecido. Se consulta al guardar, no mientras se escribe. */
export async function fetchSimilarClients(
  name: string,
  excludeId?: string,
): Promise<ClientSummary[]> {
  const { data, error } = await api.GET("/admin/clients/similar", {
    params: { query: { name, exclude_id: excludeId } },
  });
  if (error || !data) {
    throw new Error("no se pudo verificar si el cliente ya existe");
  }
  return data;
}

export function useCreateClient() {
  const queryClient = useQueryClient();
  return useMutation<Client, Error, ClientCreate>({
    mutationFn: async (nuevo) => {
      const { data, error } = await api.POST("/admin/clients", { body: nuevo });
      if (error || !data) {
        throw saveError(error, "No se pudo crear el cliente.");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLIENTS_KEY }),
  });
}

export function useUpdateClient(clientId: string) {
  const queryClient = useQueryClient();
  return useMutation<Client, Error, ClientUpdate>({
    mutationFn: async (changes) => {
      const { data, error } = await api.PATCH("/admin/clients/{client_id}", {
        params: { path: { client_id: clientId } },
        body: changes,
      });
      if (error || !data) {
        throw saveError(error, "No se pudo guardar el cliente.");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLIENTS_KEY }),
  });
}

export function useContacts(clientId: string) {
  return useQuery<Contact[]>({
    queryKey: [...CLIENTS_KEY, "contacts", clientId],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/clients/{client_id}/contacts", {
        params: { path: { client_id: clientId } },
      });
      if (error || !data) {
        throw new Error("no se pudieron cargar los contactos");
      }
      return data;
    },
  });
}

export function useCreateContact(clientId: string) {
  const queryClient = useQueryClient();
  return useMutation<Contact, Error, ContactCreate>({
    mutationFn: async (nuevo) => {
      const { data, error } = await api.POST("/admin/clients/{client_id}/contacts", {
        params: { path: { client_id: clientId } },
        body: nuevo,
      });
      if (error || !data) {
        throw saveError(error, "No se pudo agregar el contacto.");
      }
      return data;
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: [...CLIENTS_KEY, "contacts", clientId] }),
  });
}

export function useUpdateContact(clientId: string, contactId: string) {
  const queryClient = useQueryClient();
  return useMutation<Contact, Error, ContactUpdate>({
    mutationFn: async (changes) => {
      const { data, error } = await api.PATCH("/admin/clients/{client_id}/contacts/{contact_id}", {
        params: { path: { client_id: clientId, contact_id: contactId } },
        body: changes,
      });
      if (error || !data) {
        throw saveError(error, "No se pudo guardar el contacto.");
      }
      return data;
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: [...CLIENTS_KEY, "contacts", clientId] }),
  });
}

export function useSites(clientId: string, { enabled = true }: { enabled?: boolean } = {}) {
  return useQuery<Site[]>({
    queryKey: [...CLIENTS_KEY, "sites", clientId],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/clients/{client_id}/sites", {
        params: { path: { client_id: clientId } },
      });
      if (error || !data) {
        throw new Error("no se pudieron cargar los domicilios");
      }
      return data;
    },
    enabled,
  });
}

export function useCreateSite(clientId: string) {
  const queryClient = useQueryClient();
  return useMutation<Site, Error, SiteCreate>({
    mutationFn: async (nuevo) => {
      const { data, error } = await api.POST("/admin/clients/{client_id}/sites", {
        params: { path: { client_id: clientId } },
        body: nuevo,
      });
      if (error || !data) {
        throw saveError(error, "No se pudo agregar el domicilio.");
      }
      return data;
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: [...CLIENTS_KEY, "sites", clientId] }),
  });
}

export function useUpdateSite(clientId: string, siteId: string) {
  const queryClient = useQueryClient();
  return useMutation<Site, Error, SiteUpdate>({
    mutationFn: async (changes) => {
      const { data, error } = await api.PATCH("/admin/sites/{site_id}", {
        params: { path: { site_id: siteId } },
        body: changes,
      });
      if (error || !data) {
        throw saveError(error, "No se pudo guardar el domicilio.");
      }
      return data;
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: [...CLIENTS_KEY, "sites", clientId] }),
  });
}

export function useEquipment(clientId: string, siteId: string | null, deleted = false) {
  return useQuery<Equipment[]>({
    queryKey: [...CLIENTS_KEY, "equipment", clientId, { siteId, deleted }],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/clients/{client_id}/equipment", {
        params: { path: { client_id: clientId }, query: { site_id: siteId, deleted } },
      });
      if (error || !data) {
        throw new Error("no se pudieron cargar los equipos");
      }
      return data;
    },
  });
}

/** Un alta o una mudanza cambia los equipos y la cantidad de cada domicilio. */
function invalidateEquipment(queryClient: ReturnType<typeof useQueryClient>, clientId: string) {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: [...CLIENTS_KEY, "equipment", clientId] }),
    queryClient.invalidateQueries({ queryKey: [...CLIENTS_KEY, "sites", clientId] }),
  ]);
}

export function useCreateEquipment(clientId: string) {
  const queryClient = useQueryClient();
  return useMutation<Equipment, Error, EquipmentCreate>({
    mutationFn: async (nuevo) => {
      const { data, error } = await api.POST("/admin/clients/{client_id}/equipment", {
        params: { path: { client_id: clientId } },
        body: nuevo,
      });
      if (error || !data) {
        throw saveError(error, "No se pudo agregar el equipo.");
      }
      return data;
    },
    onSuccess: () => invalidateEquipment(queryClient, clientId),
  });
}

export function useUpdateEquipment(clientId: string, equipmentId: string) {
  const queryClient = useQueryClient();
  return useMutation<Equipment, Error, EquipmentUpdate>({
    mutationFn: async (changes) => {
      const { data, error } = await api.PATCH("/admin/equipment/{equipment_id}", {
        params: { path: { equipment_id: equipmentId } },
        body: changes,
      });
      if (error || !data) {
        throw saveError(error, "No se pudo guardar el equipo.");
      }
      return data;
    },
    onSuccess: () => invalidateEquipment(queryClient, clientId),
  });
}

export const HISTORY_PAGE_SIZE = 20;

/** Filtros del historial del cliente; vacío es "todos". Fechas en formato aaaa-mm-dd. */
export interface HistoryFilters {
  equipmentId: string;
  workTypeId: string;
  from: string;
  to: string;
}

/**
 * Historial de órdenes del cliente (E03-04). Cuelga de las órdenes: asignar, cerrar o
 * devolver una orden lo refresca.
 */
export function useClientOrders(clientId: string, filters: HistoryFilters, offset: number) {
  return useQuery<ClientOrderPage>({
    queryKey: [...ORDERS_KEY, "client", clientId, filters, offset],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/clients/{client_id}/orders", {
        params: {
          path: { client_id: clientId },
          query: {
            equipment_id: filters.equipmentId || undefined,
            work_type_id: filters.workTypeId || undefined,
            created_from: filters.from || undefined,
            created_to: filters.to || undefined,
            limit: HISTORY_PAGE_SIZE,
            offset,
          },
        },
      });
      if (error || !data) {
        throw new Error("no se pudo cargar el historial");
      }
      return data;
    },
    placeholderData: keepPreviousData,
  });
}

/** Clientes y equipos que coinciden con lo escrito (E03-06); desde 2 letras. */
export function useSearch(query: string, includeDeleted: boolean) {
  return useQuery<SearchResults>({
    queryKey: [...CLIENTS_KEY, "search", query, includeDeleted],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/search", {
        params: { query: { q: query, include_deleted: includeDeleted } },
      });
      if (error || !data) {
        throw new Error("no se pudo buscar");
      }
      return data;
    },
    enabled: query.length >= 2,
    placeholderData: keepPreviousData,
  });
}

/** Baja o restauración de un cliente (E03-07); invalida listas, fichas y órdenes. */
export function useClientLifecycle(clientId: string) {
  const queryClient = useQueryClient();
  return useMutation<Client, Error, "deactivation" | "restoration">({
    mutationFn: async (action) => {
      const params = { path: { client_id: clientId } };
      const { data, error } =
        action === "deactivation"
          ? await api.POST("/admin/clients/{client_id}/deactivation", { params })
          : await api.POST("/admin/clients/{client_id}/restoration", { params });
      if (error || !data) {
        throw saveError(error, "No se pudo guardar el cambio.");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLIENTS_KEY }),
  });
}

/** Bajas, restauraciones y unificaciones del cliente (E03-07, criterio 3). */
export function useClientAudit(clientId: string) {
  return useQuery<AuditEntry[]>({
    queryKey: [...CLIENTS_KEY, "audit", clientId],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/clients/{client_id}/audit", {
        params: { path: { client_id: clientId } },
      });
      if (error || !data) {
        throw new Error("no se pudo cargar la auditoría");
      }
      return data;
    },
  });
}

/** Qué se movería al unificar (E03-08, criterio 4). */
export function useMergePreview(clientId: string, intoId: string | null) {
  return useQuery<MergePreview>({
    queryKey: [...CLIENTS_KEY, "merge-preview", clientId, intoId],
    enabled: intoId !== null,
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/clients/{client_id}/merge-preview", {
        params: { path: { client_id: clientId }, query: { into_client_id: intoId ?? "" } },
      });
      if (error || !data) {
        throw saveError(error, "No se pudo calcular la unificación.");
      }
      return data;
    },
  });
}

export function useMergeClient(clientId: string) {
  const queryClient = useQueryClient();
  return useMutation<MergePreview, Error, string>({
    mutationFn: async (intoId) => {
      const { data, error } = await api.POST("/admin/clients/{client_id}/merge", {
        params: { path: { client_id: clientId } },
        body: { into_client_id: intoId },
      });
      if (error || !data) {
        throw saveError(error, "No se pudo unificar.");
      }
      return data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: CLIENTS_KEY });
      await queryClient.invalidateQueries({ queryKey: ORDERS_KEY });
    },
  });
}

type EquipmentAction =
  { kind: "deactivation" } | { kind: "restoration" } | { kind: "transfer"; siteId: string };

/** Baja, restauración (E03-07) o traslado a otro cliente (E03-09) de un equipo. */
export function useEquipmentAction(equipmentId: string) {
  const queryClient = useQueryClient();
  return useMutation<Equipment, Error, EquipmentAction>({
    mutationFn: async (action) => {
      const params = { path: { equipment_id: equipmentId } };
      const { data, error } =
        action.kind === "transfer"
          ? await api.POST("/admin/equipment/{equipment_id}/transfer", {
              params,
              body: { client_site_id: action.siteId },
            })
          : action.kind === "deactivation"
            ? await api.POST("/admin/equipment/{equipment_id}/deactivation", { params })
            : await api.POST("/admin/equipment/{equipment_id}/restoration", { params });
      if (error || !data) {
        throw saveError(error, "No se pudo guardar el cambio del equipo.");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLIENTS_KEY }),
  });
}

/** Ficha del equipo con traslados y trabajos (E03-05). */
export function useEquipmentFile(equipmentId: string) {
  return useQuery<EquipmentFile>({
    queryKey: [...CLIENTS_KEY, "equipment-file", equipmentId],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/equipment/{equipment_id}/file", {
        params: { path: { equipment_id: equipmentId } },
      });
      if (error || !data) {
        throw new Error("no se pudo cargar la ficha del equipo");
      }
      return data;
    },
  });
}
