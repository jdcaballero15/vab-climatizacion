import type { components } from "../../api/schema";

export type PendingOrder = components["schemas"]["PendingOrderOut"];
export type PendingOrderPage = components["schemas"]["PendingOrderPage"];
export type WorkOrder = components["schemas"]["WorkOrderAdminOut"];
export type WorkOrderCreate = components["schemas"]["WorkOrderCreate"];
export type OrderChannel = WorkOrderCreate["channel"];
export type Assignment = components["schemas"]["AssignmentAdminOut"];
export type AssignmentCreate = components["schemas"]["AssignmentCreate"];
