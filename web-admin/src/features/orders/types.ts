import type { components } from "../../api/schema";

export type OrderListItem = components["schemas"]["OrderListItemOut"];
export type ReturnedFromCrew = components["schemas"]["ReturnedFromCrewOut"];
export type OrderListPage = components["schemas"]["OrderListPage"];
export type WorkOrder = components["schemas"]["WorkOrderAdminOut"];
export type WorkOrderCreate = components["schemas"]["WorkOrderCreate"];
export type OrderChannel = WorkOrderCreate["channel"];
export type Assignment = components["schemas"]["AssignmentAdminOut"];
export type AssignmentCreate = components["schemas"]["AssignmentCreate"];
export type UnassignmentCreate = components["schemas"]["UnassignmentCreate"];
export type Cancellation = components["schemas"]["CancellationAdminOut"];
export type CancellationCreate = components["schemas"]["CancellationCreate"];
export type CancelReason = components["schemas"]["CancelReason"];
export type ClosureDetail = components["schemas"]["ClosureAdminOut"];
/** Los estados que lista hoy la API; Facturadas y Cobradas llegan con E04-05. */
export type ListableStatus = "pending" | "assigned" | "in_progress" | "done" | "cancelled";
