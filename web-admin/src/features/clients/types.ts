import type { components } from "../../api/schema";

export type Client = components["schemas"]["ClientAdminOut"];
export type ClientSummary = components["schemas"]["ClientSummaryOut"];
export type ClientPage = components["schemas"]["ClientPage"];
export type ClientCreate = components["schemas"]["ClientCreate"];
export type ClientUpdate = components["schemas"]["ClientUpdate"];
export type ClientSegment = Client["segment"];
export type TaxCondition = NonNullable<Client["tax_condition"]>;
export type Contact = components["schemas"]["ContactAdminOut"];
export type ContactCreate = components["schemas"]["ContactCreate"];
export type ContactUpdate = components["schemas"]["ContactUpdate"];
export type Site = components["schemas"]["SiteAdminOut"];
export type SiteCreate = components["schemas"]["SiteCreate"];
export type SiteUpdate = components["schemas"]["SiteUpdate"];
