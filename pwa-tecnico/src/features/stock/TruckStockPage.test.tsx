import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TruckStockPage } from "./TruckStockPage";

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function renderPage(body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => json(body)),
  );
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <TruckStockPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("TruckStockPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  // E08-04, criterio 4: cantidades de la camioneta, sin precios.
  it("muestra lo que lleva la camioneta", async () => {
    renderPage({
      location_name: "Camioneta 1",
      items: [{ part_name: "Gas R410A", unit: "kg", quantity: "2.500" }],
    });

    expect(await screen.findByRole("heading", { name: "Camioneta 1" })).toBeInTheDocument();
    expect(screen.getByText("2,5 kg")).toBeInTheDocument();
    expect(screen.queryByText(/\$/)).not.toBeInTheDocument();
  });

  it("avisa si la escuadrilla no tiene camioneta", async () => {
    renderPage({ location_name: null, items: [] });

    expect(await screen.findByText(/no tiene una camioneta cargada/)).toBeInTheDocument();
  });
});
