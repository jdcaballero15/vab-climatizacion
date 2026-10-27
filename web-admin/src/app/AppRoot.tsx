import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { LoginPage } from "../features/auth/LoginPage";
import { onSessionExpired } from "../features/auth/session";
import { setAccessToken, setRefreshToken } from "../features/auth/token";
import type { Session } from "../features/auth/types";
import { useLogout } from "../features/auth/useLogout";
import { AppLayout } from "./AppLayout";

export function AppRoot() {
  const [session, setSession] = useState<Session | null>(null);
  const queryClient = useQueryClient();
  const logout = useLogout();
  const navigate = useNavigate();

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

  if (!session) {
    return (
      <LoginPage
        onSuccess={(nueva) => {
          setAccessToken(nueva.access_token);
          setRefreshToken(nueva.refresh_token);
          setSession(nueva);
        }}
      />
    );
  }

  return (
    <AppLayout
      session={session}
      onLogout={() => {
        setSession(null);
        logout.mutate();
        // El próximo usuario entra a su pantalla de inicio, no a la del anterior.
        navigate("/", { replace: true });
      }}
    />
  );
}
