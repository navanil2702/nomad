"use client";

import * as React from "react";

/**
 * Google sign-in.
 *
 * With NEXT_PUBLIC_GOOGLE_CLIENT_ID set, this loads Google Identity Services
 * and decodes the returned ID token. Without it, "Continue with Google" signs
 * in a local demo profile so the whole product is usable with no credentials.
 * Either way the session lives in localStorage; swap `persist` for a Supabase
 * session when you wire the real backend auth.
 */

export interface NomadUser {
  name: string;
  email: string;
  picture?: string;
  provider: "google" | "demo";
}

interface AuthContextValue {
  user: NomadUser | null;
  ready: boolean;
  isDemo: boolean;
  signIn: () => Promise<void>;
  signOut: () => void;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);
const STORAGE_KEY = "nomad.user";
const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

const DEMO_USER: NomadUser = {
  name: "Sam Rivera",
  email: "sam@example.com",
  provider: "demo",
};

function decodeJwt(token: string): Record<string, any> {
  const payload = token.split(".")[1];
  const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
  return JSON.parse(decodeURIComponent(escape(json)));
}

function loadGoogleScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (document.getElementById("gsi-script")) return resolve();
    const script = document.createElement("script");
    script.id = "gsi-script";
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Google Identity Services"));
    document.head.appendChild(script);
  });
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<NomadUser | null>(null);
  const [ready, setReady] = React.useState(false);

  React.useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setUser(JSON.parse(raw));
    } catch {
      /* ignore malformed session */
    }
    setReady(true);
  }, []);

  const persist = React.useCallback((next: NomadUser | null) => {
    setUser(next);
    if (next) localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    else localStorage.removeItem(STORAGE_KEY);
  }, []);

  const signIn = React.useCallback(async () => {
    if (!CLIENT_ID) {
      persist(DEMO_USER);
      return;
    }
    await loadGoogleScript();
    const google = (window as any).google;
    google.accounts.id.initialize({
      client_id: CLIENT_ID,
      callback: (response: { credential: string }) => {
        const claims = decodeJwt(response.credential);
        persist({
          name: claims.name ?? "Traveller",
          email: claims.email ?? "",
          picture: claims.picture,
          provider: "google",
        });
      },
    });
    google.accounts.id.prompt();
  }, [persist]);

  const signOut = React.useCallback(() => {
    if (CLIENT_ID && (window as any).google?.accounts?.id) {
      (window as any).google.accounts.id.disableAutoSelect();
    }
    persist(null);
  }, [persist]);

  const value = React.useMemo(
    () => ({ user, ready, isDemo: !CLIENT_ID, signIn, signOut }),
    [user, ready, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
