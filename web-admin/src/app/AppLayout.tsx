import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import type { Session } from "../features/auth/types";
import { ROLE_LABELS, sectionsFor, type NavSection } from "./navigation";

interface AppLayoutProps {
  session: Session;
  onLogout: () => void;
}

/** Agrupa las secciones consecutivas que comparten título de grupo. */
function groupSections(sections: NavSection[]) {
  const groups: { title: string | null; sections: NavSection[] }[] = [];
  for (const section of sections) {
    const last = groups.at(-1);
    if (last && last.title === section.group) {
      last.sections.push(section);
    } else {
      groups.push({ title: section.group, sections: [section] });
    }
  }
  return groups;
}

/** Menú lateral con las secciones del rol y la pantalla elegida al lado. */
export function AppLayout({ session, onLogout }: AppLayoutProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const groups = groupSections(sectionsFor(session.user.role));

  return (
    <div className="layout">
      <header className="layout__topbar">
        <button
          type="button"
          className="layout__toggle"
          aria-expanded={menuOpen}
          aria-controls="main-menu"
          onClick={() => setMenuOpen((open) => !open)}
        >
          Menú
        </button>
        <span className="layout__brand">OT Platform</span>
      </header>

      <nav
        id="main-menu"
        aria-label="Menú principal"
        className={menuOpen ? "layout__nav layout__nav--open" : "layout__nav"}
      >
        <p className="layout__brand layout__brand--nav">OT Platform</p>
        {groups.map((group, index) => (
          <div key={group.title ?? `grupo-${index}`} className="layout__group">
            {group.title && <p className="layout__group-title">{group.title}</p>}
            <ul>
              {group.sections.map((section) => (
                <li key={section.path}>
                  <NavLink
                    to={section.path}
                    className="layout__link"
                    onClick={() => setMenuOpen(false)}
                  >
                    {section.label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}

        <div className="layout__user">
          <p>
            <strong>{session.user.full_name}</strong>
            <span>{ROLE_LABELS[session.user.role]}</span>
          </p>
          <button type="button" onClick={onLogout}>
            Cerrar sesión
          </button>
        </div>
      </nav>

      <main className="layout__content">
        <Outlet context={session} />
      </main>
    </div>
  );
}
