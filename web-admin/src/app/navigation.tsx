import type { ReactNode } from "react";

import type { Session } from "../features/auth/types";
import { ClientsPage } from "../features/clients/ClientsPage";
import { CrewsPage } from "../features/crews/CrewsPage";
import { EquipmentTypesPage } from "../features/equipment-types/EquipmentTypesPage";
import { FailuresPage } from "../features/failures/FailuresPage";
import { OrdersPage } from "../features/orders/OrdersPage";
import { RepairsPage } from "../features/repairs/RepairsPage";
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
  element: ReactNode;
}

// Solo administración opera órdenes, clientes, escuadrillas y catálogos
// (roles-permisos.md); dirección gestiona usuarios. El orden del arreglo es el del menú,
// y la primera sección visible es la pantalla de inicio del rol.
export const NAV_SECTIONS: NavSection[] = [
  { path: "/ordenes", label: "Órdenes", group: null, roles: ["admin"], element: <OrdersPage /> },
  { path: "/clientes", label: "Clientes", group: null, roles: ["admin"], element: <ClientsPage /> },
  {
    path: "/escuadrillas",
    label: "Escuadrillas",
    group: "Equipo",
    roles: ["admin"],
    element: <CrewsPage />,
  },
  {
    path: "/usuarios",
    label: "Usuarios",
    group: "Equipo",
    roles: ["admin", "owner"],
    element: <UsersPage />,
  },
  {
    path: "/catalogos/tipos-de-trabajo",
    label: "Tipos de trabajo",
    group: "Catálogos",
    roles: ["admin"],
    element: <WorkTypesPage />,
  },
  {
    path: "/catalogos/tipos-de-equipo",
    label: "Tipos de equipo",
    group: "Catálogos",
    roles: ["admin"],
    element: <EquipmentTypesPage />,
  },
  {
    path: "/catalogos/fallas",
    label: "Fallas",
    group: "Catálogos",
    roles: ["admin"],
    element: <FailuresPage />,
  },
  {
    path: "/catalogos/reparaciones",
    label: "Reparaciones",
    group: "Catálogos",
    roles: ["admin"],
    element: <RepairsPage />,
  },
];

export function sectionsFor(role: Role): NavSection[] {
  return NAV_SECTIONS.filter((section) => section.roles.includes(role));
}
