import { useMutation } from "@tanstack/react-query";

import { api } from "../../api/client";
import type { OrderDetail } from "./types";

type Kind = "pickup_receipt" | "delivery_receipt";

const LABELS: Record<Kind, string> = {
  pickup_receipt: "Comprobante de retiro",
  delivery_receipt: "Comprobante de devolución",
};

/**
 * Comprobantes PDF de una orden de taller, con la firma del cliente (E09-01, E09-02). La
 * primera vez se arman y se guardan; se abren con un link firmado que vence.
 */
export function ReceiptButtons({ order }: { order: OrderDetail }) {
  const open = useMutation<string, Error, Kind>({
    mutationFn: async (kind) => {
      const { data, error } = await api.POST("/admin/orders/{order_id}/documents/{kind}", {
        params: { path: { order_id: order.id, kind } },
      });
      if (error || !data) {
        const detail = (error as { detail?: { message?: unknown } } | undefined)?.detail;
        throw new Error(
          typeof detail?.message === "string" ? detail.message : "No se pudo abrir el PDF.",
        );
      }
      return data.url;
    },
    onSuccess: (url) => {
      window.open(url, "_blank", "noopener");
    },
  });

  if (order.kind !== "workshop") {
    return null;
  }
  return (
    <div className="card order-detail__card" role="group" aria-label="Comprobantes">
      <h3>Comprobantes</h3>
      <div className="clients__filters">
        {(Object.keys(LABELS) as Kind[]).map((kind) => (
          <button
            key={kind}
            type="button"
            disabled={open.isPending}
            onClick={() => open.mutate(kind)}
          >
            {LABELS[kind]}
          </button>
        ))}
      </div>
      {open.isError && (
        <p className="clients__error" role="alert">
          {open.error.message}
        </p>
      )}
    </div>
  );
}
