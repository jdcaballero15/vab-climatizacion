import { QueryClient } from "@tanstack/react-query";

// TanStack Query es la unica fuente de datos del servidor (ver web-admin/README.md).
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
});
