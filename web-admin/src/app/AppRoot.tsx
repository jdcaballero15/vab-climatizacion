import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { refreshSession } from "../api/client";
import { ChangePasswordPage } from "../features/auth/ChangePasswordPage";
import { LoginPage } from "../features/auth/LoginPage";
import { onSessionExpired } from "../features/auth/session";
import { setAccessToken } from "../features/auth/token";
import type { Session } from "../features/auth/types";
import { useLogout } from "../features/auth/useLogout";
import { AppLayout } from "./AppLayout";

export function AppRoot() {
  // undefined: todavía se está viendo si la cookie trae una sesión (E01-07).
  const [session, setSession] = useState<Session | null | undefined>(undefined);
  const queryClient = useQueryClient();
  const logout = useLogout();
  const navigate = useNavigate();

  // Al abrir o recargar, la cookie httpOnly del refresh token recupera la sesión.
  useEffect(() => {
    let vigente = true;
    void refreshSession().then((recuperada) => {
      if (vigente) {
        setSession((actual) => (actual === undefined ? recuperada : actual));
      }
    });
    return () => {
      vigente = false;
    };
  }, []);

  // Si el cliente de API no logra renovar el token (p. ej. un usuario dado de baja),
  // vuelve al login y descarta los datos del servidor.
  useEffect(
    () =>
      onSessionExpired(() => {
        queryClient.clear();
        setSession(null);
      }),
    [queryClient],
  );

  if (session === undefined) {
    return (
      <main className="login">
        <p className="muted" role="status">
          Cargando…
        </p>
      </main>
    );
  }

  if (!session) {
    return (
      <LoginPage
        onSuccess={(nueva) => {
          setAccessToken(nueva.access_token);
          setSession(nueva);
        }}
      />
    );
  }

  const onLogout = () => {
    setSession(null);
    logout.mutate();
    // El próximo usuario entra a su pantalla de inicio, no a la del anterior.
    navigate("/", { replace: true });
  };

  if (session.user.must_change_password) {
    return (
      <ChangePasswordPage
        user={session.user}
        onChanged={(user) => setSession({ ...session, user })}
        onLogout={onLogout}
      />
    );
  }

  return <AppLayout session={session} onLogout={onLogout} />;
}
