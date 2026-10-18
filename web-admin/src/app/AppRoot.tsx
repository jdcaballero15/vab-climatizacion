import { useState } from "react";

import { LoginPage } from "../features/auth/LoginPage";
import { setAccessToken } from "../features/auth/token";
import type { Session } from "../features/auth/types";
import { HomePage } from "../features/home/HomePage";

export function AppRoot() {
  const [session, setSession] = useState<Session | null>(null);

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

  return (
    <HomePage
      session={session}
      onLogout={() => {
        setAccessToken(null);
        setSession(null);
      }}
    />
  );
}
