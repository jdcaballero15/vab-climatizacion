import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CatalogCsvPage } from "./CatalogCsvPage";

function json(body: unknown) {
  return new Response(JSON.stringify(body), { headers: { "Content-Type": "application/json" } });
}

const PREVIA = {
  creates: [{ row: 3, name: "Caño de cobre", detail: "" }],
  changes: [],
  errors: [],
  unchanged: 1,
  applied: false,
};

describe("CatalogCsvPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  // E02-08: se ve qué cambia y recién después se aplica.
  it("muestra la vista previa y aplica", async () => {
    const fetchMock = vi.fn(async (request: Request) =>
      request.url.endsWith("/apply") ? json({ ...PREVIA, applied: true }) : json(PREVIA),
    );
    vi.stubGlobal("fetch", fetchMock);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <CatalogCsvPage />
      </QueryClientProvider>,
    );

    const archivo = new File(["nombre,unidad,codigo,activo\n"], "materiales.csv", {
      type: "text/csv",
    });
    await userEvent.upload(screen.getByLabelText("Archivo para importar"), archivo);
    await userEvent.click(screen.getByRole("button", { name: "Ver qué cambia" }));
    expect(await screen.findByText("Alta: Caño de cobre")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Aplicar" }));

    expect(await screen.findByRole("heading", { name: "Aplicado" })).toBeInTheDocument();
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.map(([request]) =>
          (request as Request).url.split("/").slice(-2).join("/"),
        ),
      ).toEqual(["parts/preview", "parts/apply"]),
    );
  });
});
