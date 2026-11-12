import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../../api/client";

function lastMonth(): string {
  const now = new Date();
  const date = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

/** Informe mensual del cliente en PDF, sin precios (E09-04). Por defecto, el mes pasado. */
export function MonthlyReport({ clientId }: { clientId: string }) {
  const [month, setMonth] = useState(lastMonth());
  const download = useMutation<void, Error, string>({
    mutationFn: async (period) => {
      const [year, value] = period.split("-").map(Number);
      const { data, error } = await api.GET("/admin/clients/{client_id}/monthly-report", {
        params: { path: { client_id: clientId }, query: { year, month: value } },
        parseAs: "blob",
      });
      if (error || !data) {
        const detail = (error as { detail?: { message?: unknown } } | undefined)?.detail;
        throw new Error(
          typeof detail?.message === "string" ? detail.message : "No se pudo armar el informe.",
        );
      }
      const url = URL.createObjectURL(data as Blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `informe-${period}.pdf`;
      link.click();
      URL.revokeObjectURL(url);
    },
  });

  return (
    <section className="clients__contacts" aria-label="Informe de trabajos del mes">
      <h4>Informe de trabajos del mes</h4>
      <div className="clients__filters">
        <label>
          Mes{" "}
          <input type="month" value={month} onChange={(event) => setMonth(event.target.value)} />
        </label>
        <button
          type="button"
          disabled={!month || download.isPending}
          onClick={() => download.mutate(month)}
        >
          {download.isPending ? "Armando…" : "Descargar PDF"}
        </button>
      </div>
      {download.isError && (
        <p className="clients__error" role="alert">
          {download.error.message}
        </p>
      )}
    </section>
  );
}
