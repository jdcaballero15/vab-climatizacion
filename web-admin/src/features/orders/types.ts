import type { components } from "../../api/schema";

export type OrderListItem = components["schemas"]["OrderListItemOut"];
export type ReturnedFromCrew = components["schemas"]["ReturnedFromCrewOut"];
export type OrderListPage = components["schemas"]["OrderListPage"];
export type WorkOrder = components["schemas"]["WorkOrderAdminOut"];
export type WorkOrderCreate = components["schemas"]["WorkOrderCreate"];
export type EquipmentChange = components["schemas"]["EquipmentChange"];
export type OrderChannel = WorkOrderCreate["channel"];
export type Assignment = components["schemas"]["AssignmentAdminOut"];
export type AssignmentCreate = components["schemas"]["AssignmentCreate"];
export type UnassignmentCreate = components["schemas"]["UnassignmentCreate"];
export type ReturnToCrewCreate = components["schemas"]["ReturnToCrewCreate"];
export type Cancellation = components["schemas"]["CancellationAdminOut"];
export type CancellationCreate = components["schemas"]["CancellationCreate"];
export type CancelReason = components["schemas"]["CancelReason"];
export type ClosureDetail = components["schemas"]["ClosureAdminOut"];
export type OrderDetail = components["schemas"]["WorkOrderDetailAdminOut"];
export type TimelineEntry = components["schemas"]["TimelineEntryOut"];
export type Billing = components["schemas"]["BillingAdminOut"];
export type BillingUpdate = components["schemas"]["BillingUpdate"];
export type Invoice = components["schemas"]["InvoiceOut"];
export type InvoiceCreate = components["schemas"]["InvoiceCreate"];
export type InvoiceUpdate = components["schemas"]["InvoiceUpdate"];
export type Payment = components["schemas"]["PaymentOut"];
export type PaymentCreate = components["schemas"]["PaymentCreate"];
export type PaymentVoid = components["schemas"]["PaymentVoid"];
export type PaymentMethod = components["schemas"]["PaymentMethod"];
export type Charge = components["schemas"]["ChargeAdminOut"];
export type ChargeWrite = components["schemas"]["ChargeWrite"];
export type RelatedOrder = components["schemas"]["RelatedOrderOut"];
/** Todos los estados de la orden: el panel los lista a todos (E04-05). */
export type ListableStatus = OrderListItem["status"];
/** Filtros del panel (E04-05, criterio 2). Vacío es "todas". */
export interface OrderFilters {
  crewId?: string;
  clientId?: string;
  workTypeId?: string;
  createdFrom?: string;
  createdTo?: string;
}
/** Lo que se elige en Órdenes: un estado o los equipos en el galpón (E06-07). */
export type OrderView = ListableStatus | "in_workshop";
export type WorkshopStage = components["schemas"]["WorkshopStage"];
export type OrderKind = components["schemas"]["OrderKind"];
export type OrderMaterials = components["schemas"]["OrderMaterialsAdminOut"];
export type MaterialLine = components["schemas"]["MaterialLineAdminOut"];
export type MaterialLineCreate = components["schemas"]["MaterialLineCreate"];
