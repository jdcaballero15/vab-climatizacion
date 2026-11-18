import { LogOut, Menu, PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import type { Session } from "../features/auth/types";
import { ROLE_LABELS, sectionsFor, type NavSection } from "./navigation";

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

// La elección de cerrar la barra vale para esta compu, no para el usuario.
const SIDEBAR_KEY = "ot.barra-lateral";

function initials(fullName: string): string {
  return fullName
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase())
    .join("");
}

/** Barra lateral con las secciones del rol (abierta o solo íconos), encabezado con la ruta y la
pantalla elegida. */
export function AppLayout({ session, onLogout }: AppLayoutProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(
    () => localStorage.getItem(SIDEBAR_KEY) !== "cerrada",
  );
  const SidebarIcon = sidebarOpen ? PanelLeftClose : PanelLeftOpen;

  function toggleSidebar() {
    const open = !sidebarOpen;
    setSidebarOpen(open);
    localStorage.setItem(SIDEBAR_KEY, open ? "abierta" : "cerrada");
  }
  const { pathname } = useLocation();
  const sections = sectionsFor(session.user.role);
  const groups = groupSections(sections.filter((section) => section.inMenu !== false));
  const current = sections.find((section) => pathname.startsWith(section.path));

  return (
    <div className={sidebarOpen ? "layout" : "layout layout--collapsed"}>
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
        <div className="layout__head">
          <span className="layout__mark" aria-hidden="true">
            OT
          </span>
          <span className="layout__name">OT Platform</span>
          <button
            type="button"
            className="layout__collapse btn--ghost"
            aria-expanded={sidebarOpen}
            aria-label={sidebarOpen ? "Cerrar barra lateral" : "Abrir barra lateral"}
            title={sidebarOpen ? "Cerrar barra lateral" : "Abrir barra lateral"}
            onClick={toggleSidebar}
          >
            <SidebarIcon size={16} strokeWidth={1.75} aria-hidden="true" />
          </button>
        </div>
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
            <span>{session.user.full_name}</span>{" "}
            <span className="layout__user-role">{ROLE_LABELS[session.user.role]}</span>
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
      </div>
    </div>
  );
}
