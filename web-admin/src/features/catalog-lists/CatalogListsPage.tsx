import { useQueries } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { OTHER_TEXT_KINDS, otherTextsQuery } from "../other-texts/useOtherTexts";

export interface NavTab {
  path: string;
  label: string;
  element: ReactNode;
  /** Muestra cuántos textos de las escuadrillas faltan revisar. */
  countsPending?: boolean;
}

/** Las listas que usan las órdenes, en una sola hoja con una pestaña por lista. */
export function CatalogListsPage({ tabs }: { tabs: NavTab[] }) {
  // Lo que las escuadrillas escribieron y falta revisar, para el número de la pestaña.
  const pending = useQueries({
    queries: OTHER_TEXT_KINDS.map((kind) => otherTextsQuery(kind)),
    combine: (results) =>
      results.every((result) => result.data)
        ? results.reduce((total, result) => total + (result.data?.length ?? 0), 0)
        : null,
  });

  return (
    <>
      <nav className="tabs" aria-label="Listas">
        {tabs.map((tab) => (
          <NavLink key={tab.path} to={tab.path} className="tabs__tab">
            {tab.label}
            {tab.countsPending && pending ? (
              <span className="tabs__count" aria-label={`${pending} para revisar`}>
                {pending}
              </span>
            ) : null}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </>
  );
}
