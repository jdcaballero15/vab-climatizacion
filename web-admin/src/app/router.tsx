import { Navigate, useRoutes, type RouteObject } from "react-router-dom";

import { EquipmentFilePage } from "../features/clients/EquipmentFilePage";
import { OrderDetailPage } from "../features/orders/OrderDetailPage";
import { AppRoot } from "./AppRoot";
import { NAV_SECTIONS } from "./navigation";
import { ForRole } from "./ForRole";
import { HomeRedirect, RequireRole } from "./RouteGuards";

// AppRoot pide el login antes de mostrar cualquier pantalla. La dirección pedida se
// conserva, así que después del login se abre la pantalla del link.
const routes: RouteObject[] = [
  {
    path: "/",
    element: <AppRoot />,
    children: [
      { index: true, element: <HomeRedirect /> },
      ...NAV_SECTIONS.map((section) => ({
        path: section.path.slice(1),
        element: <RequireRole roles={section.roles}>{section.element}</RequireRole>,
      })),
      // E04-06: el detalle de una orden, con el mismo permiso que Órdenes.
      {
        path: "ordenes/:orderId",
        element: (
          <RequireRole roles={["admin", "owner"]}>
            <ForRole render={(role) => <OrderDetailPage readOnly={role !== "admin"} />} />
          </RequireRole>
        ),
      },
      // E03-05: la ficha del equipo, desde la lista de equipos del cliente.
      {
        path: "equipos/:equipmentId",
        element: (
          <RequireRole roles={["admin", "owner"]}>
            <EquipmentFilePage />
          </RequireRole>
        ),
      },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
];

// Router sin loaders ni actions (BrowserRouter + useRoutes): no se usan, y el router de
// datos falla en los tests con jsdom al navegar (AbortSignal de jsdom vs. Request de Node).
export function AppRoutes() {
  return useRoutes(routes);
}
