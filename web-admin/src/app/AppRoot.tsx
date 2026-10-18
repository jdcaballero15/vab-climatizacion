import { useState } from "react";

import { LoginPage } from "../features/auth/LoginPage";
import type { Session } from "../features/auth/types";
import { HomePage } from "../features/home/HomePage";

export function AppRoot() {
  const [session, setSession] = useState<Session | null>(null);

  if (!session) {
    return <LoginPage onSuccess={setSession} />;
  }

  return <HomePage session={session} onLogout={() => setSession(null)} />;
}
