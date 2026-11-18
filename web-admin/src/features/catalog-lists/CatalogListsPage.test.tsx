import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Navigate, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CatalogListsPage, type NavTab } from "./CatalogListsPage";

const TABS: NavTab[] = [
  { path: "primera", label: "Primera", element: <h2>Pantalla primera</h2> },
  {
    path: "escrito",
    label: "Escrito por escuadrillas",
    element: <h2>Pantalla escrito</h2>,
    countsPending: true,
  },
];

function setup() {
  // Un texto pendiente por cada tipo (fallas, reparaciones, materiales): 3 en total.
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(JSON.stringify([{ text_key: "x", text: "X", count: 1 }]), {
          headers: { "Content-Type": "application/json" },
        }),
    ),
  );
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/listas"]}>
        <Routes>
          <Route path="/listas" element={<CatalogListsPage tabs={TABS} />}>
            <Route index element={<Navigate to="primera" replace />} />
            {TABS.map((tab) => (
              <Route key={tab.path} path={tab.path} element={tab.element} />
            ))}
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("CatalogListsPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("abre la primera pestaña, cambia de pestaña y cuenta lo que falta revisar", async () => {
    setup();
    const pestanas = within(screen.getByRole("navigation", { name: "Listas" }));

    expect(screen.getByRole("heading", { name: "Pantalla primera" })).toBeInTheDocument();
    expect(await pestanas.findByLabelText("3 para revisar")).toBeInTheDocument();

    await userEvent.click(pestanas.getByRole("link", { name: /Escrito por escuadrillas/ }));
    expect(screen.getByRole("heading", { name: "Pantalla escrito" })).toBeInTheDocument();
  });
});
