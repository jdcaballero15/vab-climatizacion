import { useState, type FormEvent } from "react";

import type { Session } from "./types";
import { useLogin } from "./useLogin";

interface LoginPageProps {
  onSuccess: (session: Session) => void;
}

export function LoginPage({ onSuccess }: LoginPageProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const login = useLogin();

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    login.mutate({ email, password }, { onSuccess });
  }

  return (
    <main className="login">
      <form className="login__form" onSubmit={handleSubmit} aria-label="Iniciar sesión">
        <h1 className="login__title">OT Platform</h1>
        <p className="login__subtitle">Administración</p>

        <label htmlFor="email">Correo electrónico</label>
        <input
          id="email"
          name="email"
          type="email"
          autoComplete="username"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />

        <label htmlFor="password">Contraseña</label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />

        {login.isError && (
          <p className="login__error" role="alert">
            Correo o contraseña incorrectos.
          </p>
        )}

        <button type="submit" disabled={login.isPending}>
          {login.isPending ? "Ingresando…" : "Iniciar sesión"}
        </button>
      </form>
    </main>
  );
}
