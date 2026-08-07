"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { usePathname, useRouter } from "next/navigation";
import { getAccessToken, refreshAccessToken } from "./api/client";
import { getMe, logout } from "./api/endpoints";
import type { MeResponse } from "./api/types";

type AuthStatus = "loading" | "authenticated" | "anonymous";

interface AuthContextValue {
  status: AuthStatus;
  me: MeResponse | null;
  /** Call after login/register succeeds to load the profile. */
  refresh: () => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [me, setMe] = useState<MeResponse | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await getMe();
      setMe(data);
      setStatus("authenticated");
    } catch {
      setMe(null);
      setStatus("anonymous");
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      // Session bootstrap: try to mint an access token from the httpOnly
      // refresh cookie, then load the profile.
      if (!getAccessToken()) {
        const ok = await refreshAccessToken();
        if (!ok) {
          if (!cancelled) setStatus("anonymous");
          return;
        }
      }
      if (!cancelled) await refresh();
    })();
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  const signOut = useCallback(async () => {
    try {
      await logout();
    } catch {
      // Token is cleared locally regardless.
    }
    setMe(null);
    setStatus("anonymous");
  }, []);

  const value = useMemo(
    () => ({ status, me, refresh, signOut }),
    [status, me, refresh, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

/** Wraps authed routes: redirects to /login when the session is gone. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (status === "anonymous") {
      const next = pathname && pathname !== "/" ? `?next=${encodeURIComponent(pathname)}` : "";
      router.replace(`/login${next}`);
    }
  }, [status, router, pathname]);

  if (status !== "authenticated") {
    return (
      <div className="flex min-h-[60vh] items-center justify-center" data-testid="auth-loading">
        <p className="text-sm tracking-widest text-ink-soft uppercase">Sauti…</p>
      </div>
    );
  }
  return <>{children}</>;
}

/** First name for the greeting, derived from profile or email. */
export function greetingName(me: MeResponse | null): string {
  const display = me?.profile?.display_name;
  if (display) return display;
  const email = me?.user?.email ?? "";
  const raw = email.split("@")[0] ?? "";
  if (!raw) return "friend";
  return raw.charAt(0).toUpperCase() + raw.slice(1);
}
