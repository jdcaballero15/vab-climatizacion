import type { ReactNode } from "react";
import { useOutletContext } from "react-router-dom";

import type { Session } from "../features/auth/types";

type Role = Session["user"]["role"];

/** Arma la pantalla según el rol: por ejemplo, Órdenes en modo lectura para dirección. */
export function ForRole({ render }: { render: (role: Role) => ReactNode }) {
  const session = useOutletContext<Session>();
  return render(session.user.role);
}
