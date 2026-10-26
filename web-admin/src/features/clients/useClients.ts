import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../api/client";
import type {
  Client,
  ClientCreate,
  ClientPage,
  ClientSegment,
  ClientSummary,
  ClientUpdate,
  Contact,
  ContactCreate,
  ContactUpdate,
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

export function useClientPage(segment: ClientSegment | null, offset: number) {
  return useQuery<ClientPage>({
    queryKey: [...CLIENTS_KEY, "page", { segment, offset }],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/clients", {
        params: { query: { segment, limit: PAGE_SIZE, offset } },
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

export function useSites(clientId: string) {
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
