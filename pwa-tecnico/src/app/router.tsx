import { createBrowserRouter } from "react-router-dom";

import { AppRoot } from "./AppRoot";

export const router = createBrowserRouter([
  {
    // AppRoot resuelve la sesión y adentro las rutas de la app (lista y detalle).
    path: "/*",
    element: <AppRoot />,
  },
]);
