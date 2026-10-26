import type { Session } from "../auth/types";
import { ClientsPage } from "../clients/ClientsPage";
import { EquipmentTypesPage } from "../equipment-types/EquipmentTypesPage";
import { FailuresPage } from "../failures/FailuresPage";
import { OrdersPage } from "../orders/OrdersPage";
import { RepairsPage } from "../repairs/RepairsPage";
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

      {/* Solo administración crea órdenes; dirección las verá en el panel (E04-05). */}
      {canEditCatalogs && <OrdersPage />}
      {canManageUsers && <UsersPage />}
      {/* Solo administración gestiona clientes; dirección los verá en la ficha (E03-04). */}
      {canEditCatalogs && <ClientsPage />}
      {canEditCatalogs && <WorkTypesPage />}
      {canEditCatalogs && <EquipmentTypesPage />}
      {canEditCatalogs && <FailuresPage />}
      {canEditCatalogs && <RepairsPage />}
    </main>
  );
}
