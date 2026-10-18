import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";

import { queryClient } from "./app/queryClient";
import { router } from "./app/router";
import { PwaUpdater } from "./pwa/PwaUpdater";
import "./index.css";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("No se encontró el elemento raíz #root");
}

createRoot(rootElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <PwaUpdater />
    </QueryClientProvider>
  </StrictMode>,
);
