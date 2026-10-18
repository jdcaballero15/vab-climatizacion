import { useRegisterSW } from "virtual:pwa-register/react";

export interface AppUpdate {
  needRefresh: boolean;
  update: () => void;
}

// Envuelve el registro del service worker de vite-plugin-pwa. Expone si hay una
// versión nueva pendiente y cómo aplicarla (criterio 3).
export function useAppUpdate(): AppUpdate {
  const {
    needRefresh: [needRefresh],
    updateServiceWorker,
  } = useRegisterSW();

  return {
    needRefresh,
    update: () => {
      void updateServiceWorker(true);
    },
  };
}
