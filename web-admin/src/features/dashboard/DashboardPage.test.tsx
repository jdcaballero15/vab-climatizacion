import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DashboardPage } from "./DashboardPage";
import type { Dashboard } from "./useDashboard";

const TABLERO: Dashboard = {
  date_from: "2026-10-12",
  date_to: "2026-11-10",
  by_status: [
    { key: "pending", label: "pending", count: 4, quantity: null },
    { key: "done", label: "done", count: 2, quantity: null },
  ],
  weeks: [
    { week_start: "2026-10-12", created: 3, done: 1 },
    { week_start: "2026-10-19", created: 1, done: 1 },
  ],
  totals: { date_from: "2026-10-12", date_to: "2026-11-10", created: 4, done: 2 },
  compare: { date_from: "2026-09-12", date_to: "2026-10-11", created: 6, done: 2 },
  by_technician: [{ key: "t1", label: "Ana Ficticia", count: 2, quantity: null }],
  in_progress_by_crew: [],
  top_failures: [{ key: "f1", label: "No enfría", count: 2, quantity: null }],
  top_repairs: [],
  other_failures: [{ key: "ruido", label: "Ruido", count: 3, quantity: null }],
  other_repairs: [],
  maintenance: { generated: 5, pending: 1, assigned: 2, closed: 2, cancelled: 0 },
  unbilled: [
    {
      id: "o7",
      number: 7,
      client_name: "Hotel Ficticio",
      closed_at: "2026-10-20T12:00:00Z",
      days: 21,
    },
  ],
  top_parts: [{ key: "p1", label: "Gas R410A (kg)", count: 0, quantity: "2.500" }],
};

function Location() {
  const location = useLocation();
  return <output data-testid="url">{location.search}</output>;
}

function renderDashboard(search = "") {
  const fetchMock = vi.fn(
    async (request: Request) =>
      new Response(
        JSON.stringify(new URL(request.url).pathname.endsWith("/admin/dashboard") ? TABLERO : []),
        { headers: { "Content-Type": "application/json" } },
      ),
  );
  vi.stubGlobal("fetch", fetchMock);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[`/tablero${search}`]}>
        <DashboardPage />
        <Location />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return fetchMock;
}

describe("DashboardPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  // E10-01: por estado, con link a la lista; evolución y comparación (E10-08).
  it("muestra los indicadores y lleva a la lista de un estado", async () => {
    renderDashboard();

    const pendientes = await screen.findByRole("link", { name: "Pendiente: 4" });
    expect(pendientes).toHaveAttribute("href", "/ordenes?estado=pending");
    expect(screen.getByText(/contra 6 y 2: -2 y igual/)).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "Órdenes creadas y terminadas por semana" }),
    ).toBeInTheDocument();
    const sinFacturar = within(screen.getByRole("region", { name: "Sin facturar" }));
    expect(sinFacturar.getByRole("link", { name: "N° 7" })).toHaveAttribute("href", "/ordenes/o7");
    expect(screen.getByText("Ana Ficticia")).toBeInTheDocument();
    expect(screen.getByText("2,5")).toBeInTheDocument();
    expect(screen.getByText(/Ruido \(3\)/)).toBeInTheDocument();
  });

  // E10-08, criterio 3: los filtros viajan en la dirección y llegan a la API.
  it("lee y escribe los filtros en la URL", async () => {
    const fetchMock = renderDashboard("?crew_id=c1");

    await screen.findByRole("link", { name: "Pendiente: 4" });
    const [primero] = fetchMock.mock.calls.map(([r]) => new URL((r as Request).url));
    expect(primero.searchParams.get("crew_id")).toBe("c1");

    await userEvent.type(screen.getByLabelText("Comparar desde"), "2026-09-01");
    await waitFor(() =>
      expect(screen.getByTestId("url").textContent).toContain("compare_from=2026-09-01"),
    );
  });

  it("ofrece la evolución como tabla", async () => {
    renderDashboard();

    await userEvent.click(await screen.findByRole("button", { name: "Ver tabla" }));

    const tabla = screen.getByRole("table", { name: "Órdenes por semana" });
    expect(within(tabla).getAllByRole("row")).toHaveLength(3);
  });
});
