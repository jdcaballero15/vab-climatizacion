import { LogOut, Menu } from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import type { Session } from "../features/auth/types";
import { ROLE_LABELS, sectionsFor, type NavSection } from "./navigation";
import { ThemePicker } from "./ThemePicker";

interface AppLayoutProps {
  session: Session;
  onLogout: () => void;
}

const TODAY_FORMAT = new Intl.DateTimeFormat("es-AR", {
  weekday: "long",
  day: "numeric",
  month: "long",
  timeZone: "America/Argentina/Buenos_Aires",
});

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

function initials(fullName: string): string {
  return fullName
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase())
    .join("");
}

/** Barra de íconos con las secciones del rol, encabezado con la ruta y la pantalla elegida. */
export function AppLayout({ session, onLogout }: AppLayoutProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const { pathname } = useLocation();
  const sections = sectionsFor(session.user.role);
  const groups = groupSections(sections);
  const current = sections.find((section) => pathname.startsWith(section.path));

  return (
    <div className="layout">
      <header className="layout__topbar">
        <button
          type="button"
          className="layout__toggle btn--ghost"
          aria-expanded={menuOpen}
          aria-controls="main-menu"
          onClick={() => setMenuOpen((open) => !open)}
        >
          <Menu size={18} aria-hidden="true" />
          Menú
        </button>
        <span className="layout__brand">OT Platform</span>
      </header>

      <nav
        id="main-menu"
        aria-label="Menú principal"
        className={menuOpen ? "layout__nav layout__nav--open" : "layout__nav"}
      >
        <span className="layout__mark" aria-hidden="true">
          OT
        </span>
        {groups.map((group, index) => (
          <div key={group.title ?? `grupo-${index}`} className="layout__group">
            {group.title && <p className="layout__group-title">{group.title}</p>}
            <ul>
              {group.sections.map(({ path, label, icon: Icon }) => (
                <li key={path}>
                  <NavLink to={path} className="layout__link" onClick={() => setMenuOpen(false)}>
                    <Icon size={18} strokeWidth={1.75} aria-hidden="true" />
                    <span className="layout__label">{label}</span>
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}

        <div className="layout__user">
          <span className="avatar" title={session.user.full_name} aria-hidden="true">
            {initials(session.user.full_name)}
          </span>
          <p className="layout__user-name">
            <span>{session.user.full_name}</span> <span>{ROLE_LABELS[session.user.role]}</span>
          </p>
          <button
            type="button"
            className="btn--ghost"
            aria-label="Cerrar sesión"
            title="Cerrar sesión"
            onClick={onLogout}
          >
            <LogOut size={16} strokeWidth={1.75} aria-hidden="true" />
          </button>
        </div>
      </nav>

      <div className="layout__main">
        <div className="layout__header">
          <span className="layout__crumbs">
            OT Platform
            {current && (
              <>
                <span aria-hidden="true">/</span>
                {current.group ?? "Operación"}
                <span aria-hidden="true">/</span>
                <strong>{current.label}</strong>
              </>
            )}
          </span>
          <span>{TODAY_FORMAT.format(new Date())}</span>
        </div>
        <main className="layout__content">
          <Outlet context={session} />
        </main>
        <ThemePicker />
      </div>
    </div>
  );
}
