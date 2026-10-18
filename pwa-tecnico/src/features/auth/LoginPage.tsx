import type { FormEvent } from "react";

export function LoginPage() {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    // El inicio de sesión se implementa en la historia E01-01.
  }

  return (
    <main className="login">
      <form className="login__form" onSubmit={handleSubmit} aria-label="Iniciar sesión">
        <h1 className="login__title">OT Técnico</h1>

        <label htmlFor="email">Correo electrónico</label>
        <input id="email" name="email" type="email" autoComplete="username" />

        <label htmlFor="password">Contraseña</label>
        <input id="password" name="password" type="password" autoComplete="current-password" />

        <button type="submit">Iniciar sesión</button>
      </form>
    </main>
  );
}
