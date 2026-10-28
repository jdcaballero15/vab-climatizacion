import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

import { startClosureRetry } from "./closureRetry";
import { forgetClosedOrder } from "./useMyOrders";

/** Mientras hay sesión, manda solos los cierres pendientes de este usuario (E05-13). */
export function PendingClosuresRetry({ userId }: { userId: string }) {
  const queryClient = useQueryClient();
  useEffect(
    () => startClosureRetry(userId, (orderId) => forgetClosedOrder(queryClient, orderId)),
    [userId, queryClient],
  );
  return null;
}
