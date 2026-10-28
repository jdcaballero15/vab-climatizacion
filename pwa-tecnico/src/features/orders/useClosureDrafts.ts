import { useEffect, useState } from "react";

import { listClosureDrafts, loadClosureDraft, type StoredClosure } from "./closureDrafts";

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

/** Órdenes con borrador de este usuario, para marcarlas en la lista y avisar al salir. */
export function useClosureDraftIds(userId: string) {
  const [ids, setIds] = useState<ReadonlySet<string>>(new Set());
  useEffect(() => {
    let current = true;
    void listClosureDrafts(userId).then((found) => {
      if (current) {
        setIds(new Set(found));
      }
    });
    return () => {
      current = false;
    };
  }, [userId]);
  return ids;
}
