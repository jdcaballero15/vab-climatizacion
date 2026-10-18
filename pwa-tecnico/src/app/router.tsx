import { createBrowserRouter } from "react-router-dom";

import { AppRoot } from "./AppRoot";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppRoot />,
  },
]);
