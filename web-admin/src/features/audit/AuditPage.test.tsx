import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AuditPage } from "./AuditPage";

function json(body: unknown) {
  return new Response(JSON.stringify(body), { headers: { "Content-Type": "application/json" } });
}

const CAMBIO = {
  id: "a1",
  entity: "work_type",
  entity_id: "w1",
  action: "updated",
  actor_id: "u1",
  actor_name: "Admin Ficticia",
  occurred_at: "2026-11-10T13:00:00Z",
  changes: { name: ["Instalación", "Instalación nueva"] },
  note: null,
};

describe("AuditPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  // E12-01: quién, cuándo, qué y las diferencias; se filtra por entidad.
  it("muestra los cambios y filtra por entidad", async () => {
    const fetchMock = vi.fn(async (request: Request) =>
      new URL(request.url).pathname.endsWith("/admin/users")
        ? json([])
        : json({ items: [CAMBIO], total: 1, limit: 50, offset: 0 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <AuditPage />
      </QueryClientProvider>,
    );

    const tabla = await screen.findByRole("table", { name: "Cambios registrados" });
    expect(within(tabla).getByText("Tipo de trabajo")).toBeInTheDocument();
    expect(within(tabla).getByText("Cambio")).toBeInTheDocument();
    expect(within(tabla).getByText("name: Instalación → Instalación nueva")).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText("Qué"), "client");
    await waitFor(() => {
      const urls = fetchMock.mock.calls.map(([request]) => new URL((request as Request).url));
      expect(urls.some((url) => url.searchParams.get("entity") === "client")).toBe(true);
    });
  });
});
