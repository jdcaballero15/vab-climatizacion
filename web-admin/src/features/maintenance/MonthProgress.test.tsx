import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MonthProgress } from "./MonthProgress";

describe("MonthProgress", () => {
  afterEach(() => vi.unstubAllGlobals());

  // E10-04: el avance del mes, ahora en la pantalla de Mantenimiento.
  it("muestra las visitas del mes y pide el mes entero", async () => {
    const fetchMock = vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            maintenance: { generated: 5, pending: 1, assigned: 2, closed: 2, cancelled: 0 },
          }),
          { headers: { "Content-Type": "application/json" } },
        ),
    );
    vi.stubGlobal("fetch", fetchMock);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <MonthProgress />
      </QueryClientProvider>,
    );

    const visitas = within(await screen.findByRole("region", { name: "Visitas del mes" }));
    expect(visitas.getByText("Sin asignar").nextElementSibling).toHaveTextContent("1");
    expect(visitas.getByText("Cerradas").nextElementSibling).toHaveTextContent("2");
    const [request] = fetchMock.mock.calls[0] as unknown as [Request];
    const url = new URL(request.url);
    expect(url.searchParams.get("date_from")).toMatch(/^\d{4}-\d{2}-01$/);
    expect(url.searchParams.get("date_to")).toMatch(/^\d{4}-\d{2}-(28|29|30|31)$/);
  });
});
