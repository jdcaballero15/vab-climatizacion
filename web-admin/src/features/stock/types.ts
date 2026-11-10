import type { components } from "../../api/schema";

export type StockLocation = components["schemas"]["LocationOut"];
export type LocationCreate = components["schemas"]["LocationCreate"];
export type LocationUpdate = components["schemas"]["LocationUpdate"];
export type StockPart = components["schemas"]["StockPartOut"];
export type Movement = components["schemas"]["MovementOut"];
export type ReceiptCreate = components["schemas"]["ReceiptCreate"];
export type TransferCreate = components["schemas"]["TransferCreate"];
export type AdjustmentCreate = components["schemas"]["AdjustmentCreate"];
export type MovementKind = Movement["kind"];
