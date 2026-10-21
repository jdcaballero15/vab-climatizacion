import { useState, type FormEvent } from "react";

import type { UserRole } from "./types";
import { EmailAlreadyExistsError, useCreateUser, useDeactivateUser, useUsers } from "./useUsers";

const ROLE_LABELS: Record<UserRole, string> = {
  admin: "Administración",
  technician: "Técnico",
  owner: "Dirección",
};

export function UsersPage() {
  const users = useUsers();
  const createUser = useCreateUser();
  const deactivateUser = useDeactivateUser();

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
      <h2>Usuarios</h2>

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
        <table className="users__table">
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
              <tr key={user.id}>
                <td>{user.full_name}</td>
                <td>{user.email}</td>
                <td>{ROLE_LABELS[user.role]}</td>
                <td>
                  <button
                    type="button"
                    onClick={() => deactivateUser.mutate(user.id)}
                    disabled={deactivateUser.isPending}
                  >
                    Dar de baja
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
