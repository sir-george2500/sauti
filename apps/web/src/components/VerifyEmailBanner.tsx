"use client";

import { useEffect, useState } from "react";
import { resendVerification } from "@/lib/api/endpoints";
import { useAuth } from "@/lib/auth";

/**
 * Slim, dismissable nudge for signed-in users whose email isn't verified yet.
 * Verification is NON-blocking — this banner is the only place the app
 * mentions it. Dismissal is per browser session (sessionStorage), so it
 * returns next visit without nagging within one sitting.
 *
 * Self-contained: AppShell only mounts it; all state lives here.
 */

const DISMISS_KEY = "sauti-verify-banner-dismissed";

export function VerifyEmailBanner() {
  const { me } = useAuth();
  // Render nothing until sessionStorage has been consulted on the client —
  // avoids an SSR/hydration flash of a banner the user already dismissed.
  const [ready, setReady] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [resendState, setResendState] = useState<"idle" | "sending" | "sent" | "failed">(
    "idle",
  );

  useEffect(() => {
    setDismissed(window.sessionStorage.getItem(DISMISS_KEY) === "1");
    setReady(true);
  }, []);

  if (!ready || dismissed || !me || me.email_verified !== false) return null;

  const resend = async () => {
    setResendState("sending");
    try {
      await resendVerification();
      setResendState("sent");
    } catch {
      setResendState("failed");
    }
  };

  return (
    <div
      data-testid="verify-banner"
      className="flex items-center gap-3 border-b border-accent-soft-line bg-accent-soft px-5 py-2.5 text-[13px] text-accent-deep sm:px-8"
    >
      <span className="min-w-0 truncate">
        <span className="font-semibold">Verify your email</span>
        <span className="hidden sm:inline"> — we sent a link to {me.user.email}.</span>
      </span>
      {resendState === "sent" ? (
        <span className="ml-auto flex-none font-semibold" data-testid="resend-sent">
          Sent — check your inbox
        </span>
      ) : (
        <button
          type="button"
          data-testid="resend-verification"
          onClick={resend}
          disabled={resendState === "sending"}
          className="ml-auto flex-none cursor-pointer font-semibold underline underline-offset-2 transition-colors hover:text-accent disabled:cursor-default disabled:opacity-60"
        >
          {resendState === "sending"
            ? "Sending…"
            : resendState === "failed"
              ? "Try resending"
              : "Resend link"}
        </button>
      )}
      <button
        type="button"
        aria-label="Dismiss"
        data-testid="verify-dismiss"
        onClick={() => {
          window.sessionStorage.setItem(DISMISS_KEY, "1");
          setDismissed(true);
        }}
        className="flex-none cursor-pointer px-1 text-base leading-none transition-colors hover:text-accent"
      >
        ×
      </button>
    </div>
  );
}
