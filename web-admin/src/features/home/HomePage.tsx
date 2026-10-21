import type { Session } from "../auth/types";
import { UsersPage } from "../users/UsersPage";

const ROLE_LABELS: Record<Session["user"]["role"], string> = {
  admin: "Administración",
  technician: "Técnico",
  owner: "Dirección",
};

interface HomePageProps {
  session: Session;
  onLogout: () => void;
}

export function HomePage({ session, onLogout }: HomePageProps) {
  const canManageUsers = session.user.role === "admin" || session.user.role === "owner";

  return (
    <main className="home">
      <header className="home__header">
        <div>
          <h1>Hola, {session.user.full_name}</h1>
          <p>Ingresaste como {ROLE_LABELS[session.user.role]}.</p>
        </div>
        <button type="button" onClick={onLogout}>
          Cerrar sesión
        </button>
      </header>

      {canManageUsers && <UsersPage />}
    </main>
  );
}
