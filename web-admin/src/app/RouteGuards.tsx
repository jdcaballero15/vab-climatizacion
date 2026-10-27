import type { ReactNode } from "react";
import { Navigate, useOutletContext } from "react-router-dom";

import type { Session } from "../features/auth/types";
import { ROLE_LABELS, sectionsFor, type Role } from "./navigation";

/** Pantalla de inicio: la primera sección del rol, o un saludo si no tiene ninguna. */
export function HomeRedirect() {
  const session = useOutletContext<Session>();
  const [first] = sectionsFor(session.user.role);
  if (first) {
    return <Navigate to={first.path} replace />;
  }
  return (
    <section>
      <h2>Hola, {session.user.full_name}</h2>
      <p>Ingresaste como {ROLE_LABELS[session.user.role]}.</p>
    </section>
  );
}

interface RequireRoleProps {
  roles: Role[];
  children: ReactNode;
}

/** Si el rol no ve la sección, vuelve a su pantalla de inicio. */
export function RequireRole({ roles, children }: RequireRoleProps) {
  const session = useOutletContext<Session>();
  if (!roles.includes(session.user.role)) {
    return <Navigate to="/" replace />;
  }
  return children;
}
