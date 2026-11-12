import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MonthlyReport } from "./MonthlyReport";

function renderReport() {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MonthlyReport clientId="c1" />
    </QueryClientProvider>,
  );
}

describe("MonthlyReport", () => {
  afterEach(() => vi.unstubAllGlobals());

  // E09-04: pide el PDF del mes elegido.
  it("pide el informe del mes elegido", async () => {
    const fetchMock = vi.fn(
      async () =>
        new Response(new Blob(["%PDF"]), { headers: { "Content-Type": "application/pdf" } }),
    );
    vi.stubGlobal("fetch", fetchMock);
    // jsdom no tiene URLs de blobs.
    Object.assign(URL, { createObjectURL: () => "blob:x", revokeObjectURL: () => undefined });
    renderReport();

    fireEvent.change(screen.getByLabelText("Mes"), { target: { value: "2026-10" } });
    await userEvent.click(screen.getByRole("button", { name: "Descargar PDF" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [request] = fetchMock.mock.calls[0] as unknown as [Request];
    const url = new URL(request.url);
    expect(url.pathname).toMatch(/\/admin\/clients\/c1\/monthly-report$/);
    expect(url.searchParams.get("year")).toBe("2026");
    expect(url.searchParams.get("month")).toBe("10");
  });

  // Criterio 2: sin trabajos no hay informe, y se dice.
  it("avisa si no hubo trabajos en el mes", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              detail: {
                code: "empty_report",
                message: "El cliente no tiene trabajos en ese mes: no hay informe.",
              },
            }),
            { status: 409, headers: { "Content-Type": "application/json" } },
          ),
      ),
    );
    renderReport();

    await userEvent.click(screen.getByRole("button", { name: "Descargar PDF" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("no tiene trabajos en ese mes");
  });
});
