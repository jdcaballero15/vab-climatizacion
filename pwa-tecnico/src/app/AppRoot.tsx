import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Navigate, Route, Routes } from "react-router-dom";

import { refreshSession } from "../api/client";
import { LoginPage } from "../features/auth/LoginPage";
import { onSessionExpired } from "../features/auth/session";
import { setAccessToken } from "../features/auth/token";
import type { Session } from "../features/auth/types";
import { useLogout } from "../features/auth/useLogout";
import { ClosurePage } from "../features/orders/ClosurePage";
import { MyOrdersPage } from "../features/orders/MyOrdersPage";
import { OrderDetailPage } from "../features/orders/OrderDetailPage";

export function AppRoot() {
  // undefined: todavía se está viendo si la cookie trae una sesión (E01-07).
  const [session, setSession] = useState<Session | null | undefined>(undefined);
  const queryClient = useQueryClient();
  const logout = useLogout();

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
        <p className="orders__message" role="status">
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
  };

  return (
    <Routes>
      <Route path="/" element={<MyOrdersPage onLogout={onLogout} />} />
      <Route path="/ordenes/:orderId" element={<OrderDetailPage />} />
      <Route path="/ordenes/:orderId/cerrar" element={<ClosurePage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
