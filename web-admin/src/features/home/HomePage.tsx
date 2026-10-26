import type { Session } from "../auth/types";
import { EquipmentTypesPage } from "../equipment-types/EquipmentTypesPage";
import { FailuresPage } from "../failures/FailuresPage";
import { UsersPage } from "../users/UsersPage";
import { WorkTypesPage } from "../work-types/WorkTypesPage";

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
  // Solo administración edita catálogos (roles-permisos.md); la API lo exige igual.
  const canEditCatalogs = session.user.role === "admin";

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
      {canEditCatalogs && <WorkTypesPage />}
      {canEditCatalogs && <EquipmentTypesPage />}
      {canEditCatalogs && <FailuresPage />}
    </main>
  );
}
