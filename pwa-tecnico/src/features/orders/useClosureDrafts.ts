import { useEffect, useState } from "react";

import {
  listStoredClosures,
  loadClosureDraft,
  onClosureDraftsChanged,
  type StoredClosure,
} from "./closureDrafts";

/** Borrador guardado de una orden: `undefined` mientras se lee del celular. */
export function useStoredClosure(userId: string, orderId: string) {
  const [stored, setStored] = useState<StoredClosure | null | undefined>(undefined);
  useEffect(() => {
    let current = true;
    void loadClosureDraft(userId, orderId).then((found) => {
      if (current) {
        setStored(found);
      }
    });
    return () => {
      current = false;
    };
  }, [userId, orderId]);
  return stored;
}

/**
 * Cierres guardados de este usuario, para marcarlos en la lista y avisar al salir. Se
 * actualiza solo cuando el reintento manda uno o lo marca rechazado. `undefined` mientras
 * se lee del celular.
 */
export function useStoredClosures(userId: string) {
  const [closures, setClosures] = useState<StoredClosure[] | undefined>(undefined);
  useEffect(() => {
    let current = true;
    const load = () =>
      void listStoredClosures(userId).then((found) => {
        if (current) {
          setClosures(found);
        }
      });
    load();
    const stop = onClosureDraftsChanged(load);
    return () => {
      current = false;
      stop();
    };
  }, [userId]);
  return closures;
}
