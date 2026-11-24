import { Fragment, useState, type FormEvent } from "react";
import { Link, useOutletContext } from "react-router-dom";

import { ResetPasswordPanel } from "./ResetPasswordPanel";
import type { UserRole } from "./types";
import {
  EmailAlreadyExistsError,
  useCreateUser,
  useDeactivateUser,
  useDeactivatedUsers,
  useReactivateUser,
  useUnlockUser,
  useUsers,
} from "./useUsers";
import { PageHeader } from "../../app/PageHeader";
import type { Session } from "../auth/types";

const ROLE_LABELS: Record<UserRole, string> = {
  admin: "Administración",
  technician: "Técnico",
  owner: "Dirección",
};

const DATE = new Intl.DateTimeFormat("es-AR", { dateStyle: "short" });
const TIME = new Intl.DateTimeFormat("es-AR", { hour: "2-digit", minute: "2-digit" });

function formatDate(iso: string): string {
  return DATE.format(new Date(iso));
}

function formatTime(iso: string): string {
  return TIME.format(new Date(iso));
}

export function UsersPage() {
  // La sesión llega por el Outlet de AppLayout; puede faltar fuera del router (tests).
  const session = useOutletContext<Session | undefined>();
  const users = useUsers();
  const createUser = useCreateUser();
  const deactivateUser = useDeactivateUser();
  const unlockUser = useUnlockUser();
  const deactivated = useDeactivatedUsers();
  const reactivateUser = useReactivateUser();
  const [resetting, setResetting] = useState<string | null>(null);

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<UserRole>("technician");
  const [password, setPassword] = useState("");

  function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createUser.mutate(
      { full_name: fullName, email, role, password },
      {
        onSuccess: () => {
          setFullName("");
          setEmail("");
          setRole("technician");
          setPassword("");
        },
      },
    );
  }

  return (
    <section className="users">
      <PageHeader
        eyebrow="Equipo"
        title="Usuarios"
        subtitle="Quién entra al sistema y con qué rol. Cada escuadrilla usa el usuario de su celular."
        actions={
          <Link to="/auditoria" className="btn btn--sm">
            Ver auditoría
          </Link>
        }
      />

      <form className="users__form" onSubmit={handleCreate} aria-label="Crear usuario">
        <h3>Nuevo usuario</h3>

        <label htmlFor="full_name">Nombre</label>
        <input
          id="full_name"
          value={fullName}
          onChange={(event) => setFullName(event.target.value)}
          required
        />

        <label htmlFor="email">Correo electrónico</label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />

        <label htmlFor="role">Rol</label>
        <select
          id="role"
          value={role}
          onChange={(event) => setRole(event.target.value as UserRole)}
        >
          {Object.entries(ROLE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>

        <label htmlFor="password">Contraseña inicial</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
          minLength={8}
        />

        {createUser.isError && (
          <p className="users__error" role="alert">
            {createUser.error instanceof EmailAlreadyExistsError
              ? "Ya existe un usuario con ese correo."
              : "No se pudo crear el usuario."}
          </p>
        )}

        <button type="submit" disabled={createUser.isPending}>
          {createUser.isPending ? "Creando…" : "Crear usuario"}
        </button>
      </form>

      {users.isLoading && <p>Cargando usuarios…</p>}
      {users.isError && <p role="alert">No se pudieron cargar los usuarios.</p>}

      {users.data && (
        <table className="users__table" aria-label="Usuarios activos">
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Correo</th>
              <th>Rol</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {users.data.map((user) => (
              <Fragment key={user.id}>
                <tr>
                  <td>{user.full_name}</td>
                  <td>{user.email}</td>
                  <td>
                    {ROLE_LABELS[user.role]}
                    {user.locked_until && (
                      <span className="badge badge--danger">
                        Bloqueado hasta las {formatTime(user.locked_until)}
                      </span>
                    )}
                  </td>
                  <td>
                    <div className="users__actions">
                      {user.locked_until && (
                        <button
                          type="button"
                          onClick={() => unlockUser.mutate(user.id)}
                          disabled={unlockUser.isPending}
                        >
                          Desbloquear
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => setResetting(user.id)}
                        disabled={resetting === user.id}
                      >
                        Restablecer contraseña
                      </button>
                      <button
                        type="button"
                        onClick={() => deactivateUser.mutate(user.id)}
                        disabled={deactivateUser.isPending}
                      >
                        Dar de baja
                      </button>
                    </div>
                  </td>
                </tr>
                {resetting === user.id && (
                  <tr className="users__panel">
                    <td colSpan={4}>
                      <ResetPasswordPanel
                        user={user}
                        self={user.id === session?.user.id}
                        onClose={() => setResetting(null)}
                      />
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      )}

      <section className="users__deactivated" aria-labelledby="users-deactivated-title">
        <h3 id="users-deactivated-title">Dados de baja</h3>
        {deactivated.isLoading && <p>Cargando…</p>}
        {deactivated.isError && (
          <p role="alert">No se pudieron cargar los usuarios dados de baja.</p>
        )}
        {reactivateUser.isError && (
          <p className="users__error" role="alert">
            No se pudo reactivar el usuario. Probá de nuevo.
          </p>
        )}
        {deactivated.data?.length === 0 && <p>No hay usuarios dados de baja.</p>}
        {deactivated.data && deactivated.data.length > 0 && (
          <table className="users__table">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Correo</th>
                <th>Rol</th>
                <th>Baja</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {deactivated.data.map((user) => (
                <tr key={user.id}>
                  <td>{user.full_name}</td>
                  <td>{user.email}</td>
                  <td>{ROLE_LABELS[user.role]}</td>
                  <td>{user.deleted_at && formatDate(user.deleted_at)}</td>
                  <td>
                    <div className="users__actions">
                      <button
                        type="button"
                        onClick={() => reactivateUser.mutate(user.id)}
                        disabled={reactivateUser.isPending}
                      >
                        Reactivar
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </section>
  );
}
