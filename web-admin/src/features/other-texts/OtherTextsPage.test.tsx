import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { OtherTextsPage } from "./OtherTextsPage";

function json(body: unknown, status = 200) {
  return new Response(status === 204 ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function setup() {
  const fetchMock = vi.fn(async (request: Request) => {
    const url = new URL(request.url);
    if (url.pathname.endsWith("/admin/other-texts")) {
      return json([{ text_key: "burlete roto", text: "Burlete roto", count: 3 }]);
    }
    if (url.pathname.endsWith("/promote")) {
      return json({ updated: 3 });
    }
    if (url.pathname.endsWith("/dismiss")) {
      return json(null, 204);
    }
    return json([]);
  });
  vi.stubGlobal("fetch", fetchMock);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <OtherTextsPage />
    </QueryClientProvider>,
  );
  return fetchMock;
}

function posts(fetchMock: ReturnType<typeof setup>, end: string) {
  return fetchMock.mock.calls
    .map(([request]) => request as Request)
    .filter((request) => request.method === "POST" && request.url.endsWith(end));
}

describe("OtherTextsPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  // E02-07, criterios 1 y 2: cada texto con sus repeticiones; se suma a la lista.
  it("suma un texto repetido a la lista", async () => {
    const fetchMock = setup();

    const fila = within(await screen.findByRole("listitem", { name: "Burlete roto" }));
    expect(fila.getByText("3 veces")).toBeInTheDocument();
    await userEvent.click(fila.getByRole("button", { name: "Sumar a la lista" }));
    await userEvent.click(fila.getByRole("button", { name: "Confirmar" }));

    await waitFor(() => expect(posts(fetchMock, "/promote")).toHaveLength(1));
    expect(await posts(fetchMock, "/promote")[0].json()).toMatchObject({
      kind: "failure",
      text_key: "burlete roto",
      name: "Burlete roto",
      target_id: null,
    });
  });

  // Criterio 3: se descarta.
  it("descarta un texto", async () => {
    const fetchMock = setup();

    const fila = within(await screen.findByRole("listitem", { name: "Burlete roto" }));
    await userEvent.click(fila.getByRole("button", { name: "Descartar" }));

    await waitFor(() => expect(posts(fetchMock, "/dismiss")).toHaveLength(1));
  });
});
