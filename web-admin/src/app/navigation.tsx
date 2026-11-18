import {
  LayoutDashboard,
  ListChecks,
  Boxes,
  FileSpreadsheet,
  History,
  Building2,
  CalendarClock,
  ClipboardList,
  Package,
  Truck,
  Users,
  type LucideIcon,
} from "lucide-react";
import type { ReactNode } from "react";

import { ForRole } from "./ForRole";

import type { Session } from "../features/auth/types";
import { AuditPage } from "../features/audit/AuditPage";
import { CatalogListsPage, type NavTab } from "../features/catalog-lists/CatalogListsPage";
import { CatalogCsvPage } from "../features/catalog-csv/CatalogCsvPage";
import { ClientsPage } from "../features/clients/ClientsPage";
import { DashboardPage } from "../features/dashboard/DashboardPage";
import { CrewsPage } from "../features/crews/CrewsPage";
import { EquipmentTypesPage } from "../features/equipment-types/EquipmentTypesPage";
import { FailuresPage } from "../features/failures/FailuresPage";
import { MaintenancePage } from "../features/maintenance/MaintenancePage";
import { OrdersPage } from "../features/orders/OrdersPage";
import { OtherTextsPage } from "../features/other-texts/OtherTextsPage";
import { PartsPage } from "../features/parts/PartsPage";
import { RepairsPage } from "../features/repairs/RepairsPage";
import { StockPage } from "../features/stock/StockPage";
import { UsersPage } from "../features/users/UsersPage";
import { WorkTypesPage } from "../features/work-types/WorkTypesPage";

export type Role = Session["user"]["role"];

export const ROLE_LABELS: Record<Role, string> = {
  admin: "Administración",
  technician: "Técnico",
  owner: "Dirección",
};

export interface NavSection {
  path: string;
  label: string;
  /** Título del grupo en el menú; null = sin título. */
  group: string | null;
  /** Roles que ven la sección. La API exige el rol igual: esto solo ordena la interfaz. */
  roles: Role[];
  /** Roles para los que es la pantalla de inicio, aunque no sea la primera del menú. */
  homeFor?: Role[];
  /** false = no va en la barra lateral; se llega desde otra pantalla. */
  inMenu?: boolean;
  icon: LucideIcon;
  element: ReactNode;
  /** Pestañas de la pantalla: cada una con su ruta debajo de la de la sección. */
  tabs?: NavTab[];
}

const LIST_TABS: NavTab[] = [
  { path: "tipos-de-trabajo", label: "Tipos de trabajo", element: <WorkTypesPage /> },
  { path: "tipos-de-equipo", label: "Tipos de equipo", element: <EquipmentTypesPage /> },
  { path: "fallas", label: "Fallas", element: <FailuresPage /> },
  { path: "reparaciones", label: "Reparaciones", element: <RepairsPage /> },
  {
    path: "escrito-por-escuadrillas",
    label: "Escrito por escuadrillas",
    element: <OtherTextsPage />,
    countsPending: true,
  },
];

// Solo administración opera órdenes, clientes, escuadrillas y catálogos
// (roles-permisos.md); dirección ve las órdenes y gestiona usuarios. El orden del arreglo es el del menú,
// y la primera sección visible es la pantalla de inicio del rol.
export const NAV_SECTIONS: NavSection[] = [
  {
    path: "/tablero",
    label: "Tablero",
    group: null,
    roles: ["admin", "owner"],
    // E10-07: dirección entra al tablero; administración, a Órdenes.
    homeFor: ["owner"],
    icon: LayoutDashboard,
    element: <DashboardPage />,
  },
  {
    path: "/ordenes",
    label: "Órdenes",
    group: null,
    // Dirección ve el panel en modo lectura (E04-05, criterio 5).
    roles: ["admin", "owner"],
    icon: ClipboardList,
    element: <ForRole render={(role) => <OrdersPage readOnly={role !== "admin"} />} />,
  },
  {
    path: "/mantenimiento",
    label: "Mantenimiento",
    group: null,
    roles: ["admin"],
    icon: CalendarClock,
    element: <MaintenancePage />,
  },
  {
    path: "/stock",
    label: "Stock",
    group: null,
    // Dirección ve el stock sin moverlo (roles-permisos.md).
    roles: ["admin", "owner"],
    icon: Boxes,
    element: <ForRole render={(role) => <StockPage readOnly={role !== "admin"} />} />,
  },
  {
    path: "/clientes",
    label: "Clientes",
    group: null,
    roles: ["admin"],
    icon: Building2,
    element: <ClientsPage />,
  },
  {
    path: "/escuadrillas",
    label: "Escuadrillas",
    group: "Equipo",
    roles: ["admin"],
    icon: Truck,
    element: <CrewsPage />,
  },
  {
    path: "/usuarios",
    label: "Usuarios",
    group: "Equipo",
    roles: ["admin", "owner"],
    icon: Users,
    element: <UsersPage />,
  },
  {
    path: "/auditoria",
    label: "Auditoría",
    group: "Equipo",
    roles: ["admin", "owner"],
    icon: History,
    // Desde Usuarios: para investigar algo puntual, no para el día a día.
    inMenu: false,
    element: <AuditPage />,
  },
  {
    path: "/catalogos/listas",
    label: "Listas",
    group: "Catálogos",
    roles: ["admin"],
    icon: ListChecks,
    element: <CatalogListsPage tabs={LIST_TABS} />,
    tabs: LIST_TABS,
  },
  {
    path: "/catalogos/materiales",
    label: "Materiales y precios",
    group: "Catálogos",
    roles: ["admin"],
    icon: Package,
    element: <PartsPage />,
  },
  {
    path: "/catalogos/importar",
    label: "Importar y exportar",
    group: "Catálogos",
    roles: ["admin"],
    icon: FileSpreadsheet,
    element: <CatalogCsvPage />,
  },
];

export function sectionsFor(role: Role): NavSection[] {
  return NAV_SECTIONS.filter((section) => section.roles.includes(role));
}

/** La pantalla de inicio del rol: la marcada para él o, si no, la primera que ve. */
export function homeFor(role: Role): NavSection | undefined {
  const sections = sectionsFor(role);
  return (
    sections.find((section) => section.homeFor?.includes(role)) ??
    sections.find((section) => !section.homeFor)
  );
}
