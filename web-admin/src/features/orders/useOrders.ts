import {
  keepPreviousData,
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api } from "../../api/client";
import type { ClientPage } from "../clients/types";
import type {
  Assignment,
  Billing,
  BillingUpdate,
  Charge,
  ChargeWrite,
  Invoice,
  InvoiceCreate,
  InvoiceUpdate,
  OrderFilters,
  PaymentCreate,
  PaymentVoid,
  AssignmentCreate,
  UnassignmentCreate,
  Cancellation,
  CancellationCreate,
  ClosureDetail,
  OrderView,
  OrderListPage,
  OrderDetail,
  EquipmentChange,
  ReturnToCrewCreate,
  WorkOrder,
  WorkOrderCreate,
} from "./types";

export const ORDERS_KEY = ["orders"] as const;
export const PAGE_SIZE = 50;
// Clientes que muestra el selector de la orden; con más, se sigue escribiendo para filtrar.
export const CLIENT_OPTIONS_LIMIT = 20;

/** Error con el mensaje en español que manda el backend ({code, message}), si lo hay. */
export function saveError(error: unknown, fallback: string): Error {
  const detail = (error as { detail?: { message?: unknown } } | undefined)?.detail;
  return new Error(typeof detail?.message === "string" ? detail.message : fallback);
}

/** Una página de órdenes de un estado, o de las que están en el galpón (E06-07). */
async function fetchOrders(
  view: OrderView,
  limit: number,
  offset: number,
  filters: OrderFilters = {},
) {
  return view === "in_workshop"
    ? api.GET("/admin/orders/in-workshop", { params: { query: { limit, offset } } })
    : api.GET("/admin/orders", {
        params: {
          query: {
            status: view,
            limit,
            offset,
            crew_id: filters.crewId || undefined,
            client_id: filters.clientId || undefined,
            work_type_id: filters.workTypeId || undefined,
            created_from: filters.createdFrom || undefined,
            created_to: filters.createdTo || undefined,
          },
        },
      });
}

export function useOrderList(status: OrderView, offset: number, filters: OrderFilters = {}) {
  return useQuery<OrderListPage>({
    queryKey: [...ORDERS_KEY, status, { offset, filters }],
    queryFn: async () => {
      const { data, error } = await fetchOrders(status, PAGE_SIZE, offset, filters);
      if (error || !data) {
        throw new Error("no se pudieron cargar las órdenes");
      }
      return data;
    },
    placeholderData: keepPreviousData,
  });
}

/** Cuántas órdenes hay en cada estado, con los filtros del panel: el total de una página
 * de una sola orden. */
export function useOrderCounts(statuses: OrderView[], filters: OrderFilters = {}) {
  const results = useQueries({
    queries: statuses.map((status) => ({
      queryKey: [...ORDERS_KEY, status, "count", filters],
      queryFn: async () => {
        // Los filtros no aplican al galpón: es una vista aparte (E06-07).
        const { data, error } = await fetchOrders(status, 1, 0, filters);
        if (error || !data) {
          throw new Error("no se pudo contar las órdenes");
        }
        return data.total;
      },
    })),
  });
  return Object.fromEntries(
    statuses.map((status, index) => [status, results[index]?.data]),
  ) as Partial<Record<OrderView, number>>;
}

export function useCreateOrder() {
  const queryClient = useQueryClient();
  return useMutation<WorkOrder, Error, WorkOrderCreate>({
    mutationFn: async (nueva) => {
      const { data, error } = await api.POST("/admin/orders", { body: nueva });
      if (error || !data) {
        throw saveError(error, "No se pudo crear la orden.");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ORDERS_KEY }),
  });
}

/** Importes, factura y cobro de una orden cerrada (E04-09 a E04-11). */
export function useOrderBilling(orderId: string) {
  return useQuery<Billing>({
    queryKey: [...ORDERS_KEY, orderId, "billing"],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/orders/{order_id}/billing", {
        params: { path: { order_id: orderId } },
      });
      if (error || !data) {
        throw new Error("no se pudieron cargar los importes");
      }
      return data;
    },
  });
}

/** Guarda la mano de obra de una terminada (E04-14). */
export function useSaveBilling(orderId: string) {
  const queryClient = useQueryClient();
  return useMutation<Billing, Error, BillingUpdate>({
    mutationFn: async (cobro) => {
      const { data, error } = await api.PUT("/admin/orders/{order_id}/billing", {
        params: { path: { order_id: orderId } },
        body: cobro,
      });
      if (error || !data) {
        throw saveError(error, "No se pudo guardar la mano de obra.");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ORDERS_KEY }),
  });
}

/** Otros cargos de la orden (E04-11). */
export function useCharges(orderId: string) {
  return useQuery<Charge[]>({
    queryKey: [...ORDERS_KEY, orderId, "charges"],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/orders/{order_id}/charges", {
        params: { path: { order_id: orderId } },
      });
      if (error || !data) {
        throw new Error("no se pudieron cargar los cargos");
      }
      return data;
    },
  });
}

type ChargeChange =
  | { kind: "add"; body: ChargeWrite }
  | { kind: "update"; chargeId: string; body: ChargeWrite }
  | { kind: "remove"; chargeId: string };

/** Agrega, corrige o saca un cargo; cada cambio queda en la línea de tiempo. */
export function useChangeCharge(orderId: string) {
  const queryClient = useQueryClient();
  return useMutation<Charge[], Error, ChargeChange>({
    mutationFn: async (change) => {
      const path = { order_id: orderId };
      const { data, error } =
        change.kind === "add"
          ? await api.POST("/admin/orders/{order_id}/charges", {
              params: { path },
              body: change.body,
            })
          : change.kind === "update"
            ? await api.PUT("/admin/orders/{order_id}/charges/{charge_id}", {
                params: { path: { ...path, charge_id: change.chargeId } },
                body: change.body,
              })
            : await api.DELETE("/admin/orders/{order_id}/charges/{charge_id}", {
                params: { path: { ...path, charge_id: change.chargeId } },
              });
      if (error || !data) {
        throw saveError(error, "No se pudo guardar el cargo.");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ORDERS_KEY }),
  });
}

/** Una factura para una o varias terminadas aprobadas (E04-09). */
export function useCreateInvoice() {
  const queryClient = useQueryClient();
  return useMutation<Invoice, Error, InvoiceCreate>({
    mutationFn: async (factura) => {
      const { data, error } = await api.POST("/admin/invoices", { body: factura });
      if (error || !data) {
        throw saveError(error, "No se pudo registrar la factura.");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ORDERS_KEY }),
  });
}

/** Corrige número o fecha de una factura (E04-09, criterio 4). */
export function useUpdateInvoice(invoiceId: string) {
  const queryClient = useQueryClient();
  return useMutation<Invoice, Error, InvoiceUpdate>({
    mutationFn: async (factura) => {
      const { data, error } = await api.PUT("/admin/invoices/{invoice_id}", {
        params: { path: { invoice_id: invoiceId } },
        body: factura,
      });
      if (error || !data) {
        throw saveError(error, "No se pudo corregir la factura.");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ORDERS_KEY }),
  });
}

/** Registra el cobro (E04-10) o lo anula con motivo (criterio 4). */
export function usePayment(orderId: string) {
  const queryClient = useQueryClient();
  return useMutation<
    Billing,
    Error,
    { kind: "register"; body: PaymentCreate } | { kind: "void"; body: PaymentVoid }
  >({
    mutationFn: async (change) => {
      const params = { path: { order_id: orderId } };
      const { data, error } =
        change.kind === "register"
          ? await api.POST("/admin/orders/{order_id}/payment", { params, body: change.body })
          : await api.POST("/admin/orders/{order_id}/payment/void", { params, body: change.body });
      if (error || !data) {
        throw saveError(
          error,
          change.kind === "register" ? "No se pudo registrar el cobro." : "No se pudo anular.",
        );
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ORDERS_KEY }),
  });
}

/** Agrega, cambia o saca el equipo de una orden Pendiente o Asignada (E04-12). */
export function useChangeEquipment(orderId: string) {
  const queryClient = useQueryClient();
  return useMutation<WorkOrder, Error, EquipmentChange>({
    mutationFn: async (cambio) => {
      const { data, error } = await api.PUT("/admin/orders/{order_id}/equipment", {
        params: { path: { order_id: orderId } },
        body: cambio,
      });
      if (error || !data) {
        throw saveError(error, "No se pudo cambiar el equipo.");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ORDERS_KEY }),
  });
}

export function useAssignOrder(orderId: string) {
  const queryClient = useQueryClient();
  return useMutation<Assignment, Error, AssignmentCreate>({
    mutationFn: async (asignacion) => {
      const { data, error } = await api.POST("/admin/orders/{order_id}/assignment", {
        params: { path: { order_id: orderId } },
        body: asignacion,
      });
      if (error || !data) {
        throw saveError(error, "No se pudo asignar la orden.");
      }
      return data;
    },
    // La orden deja de estar pendiente: se refresca el listado.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ORDERS_KEY }),
  });
}

/** Otra escuadrilla o fecha para una orden Asignada o En curso (E04-04). */
export function useReassignOrder(orderId: string) {
  const queryClient = useQueryClient();
  return useMutation<Assignment, Error, AssignmentCreate>({
    mutationFn: async (asignacion) => {
      const { data, error } = await api.POST("/admin/orders/{order_id}/reassignment", {
        params: { path: { order_id: orderId } },
        body: asignacion,
      });
      if (error || !data) {
        throw saveError(error, "No se pudo reasignar la orden.");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ORDERS_KEY }),
  });
}

/** Devuelve una orden Asignada a Pendientes (E04-04). */
export function useUnassignOrder(orderId: string) {
  const queryClient = useQueryClient();
  return useMutation<void, Error, UnassignmentCreate>({
    mutationFn: async (desasignacion) => {
      const { error } = await api.POST("/admin/orders/{order_id}/unassignment", {
        params: { path: { order_id: orderId } },
        body: desasignacion,
      });
      if (error) {
        throw saveError(error, "No se pudo desasignar la orden.");
      }
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ORDERS_KEY }),
  });
}

/** Devuelve una Terminada a la escuadrilla que la cerró, con motivo (E04-08). */
export function useReturnOrder(orderId: string) {
  const queryClient = useQueryClient();
  return useMutation<Assignment, Error, ReturnToCrewCreate>({
    mutationFn: async (devolucion) => {
      const { data, error } = await api.POST("/admin/orders/{order_id}/return", {
        params: { path: { order_id: orderId } },
        body: devolucion,
      });
      if (error || !data) {
        throw saveError(error, "No se pudo devolver la orden.");
      }
      return data;
    },
    // Pasa de Terminadas a Asignadas: se refrescan todos los listados.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ORDERS_KEY }),
  });
}

export function useCancelOrder(orderId: string) {
  const queryClient = useQueryClient();
  return useMutation<Cancellation, Error, CancellationCreate>({
    mutationFn: async (cancelacion) => {
      const { data, error } = await api.POST("/admin/orders/{order_id}/cancellation", {
        params: { path: { order_id: orderId } },
        body: cancelacion,
      });
      if (error || !data) {
        throw saveError(error, "No se pudo cancelar la orden.");
      }
      return data;
    },
    // La orden pasa a Canceladas: se refrescan todos los listados.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ORDERS_KEY }),
  });
}

const PHOTO_URL_REFRESH_MS = 4 * 60 * 1000;

/** La orden con todos sus datos y su línea de tiempo (E04-06). */
export function useOrderDetail(orderId: string) {
  return useQuery<OrderDetail>({
    queryKey: [...ORDERS_KEY, "detail", orderId],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/orders/{order_id}", {
        params: { path: { order_id: orderId } },
      });
      if (error || !data) {
        throw new Error("no se pudo cargar la orden");
      }
      return data;
    },
  });
}

/** Lo que cargó la escuadrilla en el último cierre (E04-08, criterio 1). */
export function useOrderClosure(orderId: string) {
  return useQuery<ClosureDetail>({
    queryKey: [...ORDERS_KEY, orderId, "closure"],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/orders/{order_id}/closure", {
        params: { path: { order_id: orderId } },
      });
      if (error || !data) {
        throw new Error("no se pudo cargar el cierre");
      }
      return data;
    },
    // Las URLs de las fotos vencen a los 5 minutos (E00-09): se renuevan antes.
    staleTime: PHOTO_URL_REFRESH_MS,
    refetchInterval: PHOTO_URL_REFRESH_MS,
  });
}

/** Clientes cuyo nombre contiene el texto, sin distinguir mayúsculas ni acentos. */
/** Clientes para elegir en la orden: por nombre (o parte) o número; sin texto, los primeros. */
export function useClientOptions(text: string, enabled: boolean) {
  const q = text.trim();
  return useQuery<ClientPage>({
    queryKey: ["clients", "options", q],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/clients", {
        params: { query: { q: q || undefined, limit: CLIENT_OPTIONS_LIMIT } },
      });
      if (error || !data) {
        throw new Error("no se pudieron buscar los clientes");
      }
      return data;
    },
    enabled,
    placeholderData: keepPreviousData,
  });
}
