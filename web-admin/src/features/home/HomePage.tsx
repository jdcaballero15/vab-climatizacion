import type { Session } from "../auth/types";

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
  return (
    <main className="home">
      <h1>Hola, {session.user.full_name}</h1>
      <p>Ingresaste como {ROLE_LABELS[session.user.role]}.</p>
      <button type="button" onClick={onLogout}>
        Cerrar sesión
      </button>
    </main>
  );
}
