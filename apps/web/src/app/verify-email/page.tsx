"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { verifyEmail } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth";
import { btnPrimary, ErrorNote } from "@/components/ui";

function messageFor(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.code === "TOKEN_USED")
      return "This link was already used — if that was you, you're all set.";
    if (err.code === "TOKEN_EXPIRED")
      return "This link has expired. Sign in and use “Resend link” to get a fresh one.";
    if (err.status === 400 || err.status === 422)
      return "This verification link isn't valid. Sign in and request a new one.";
  }
  return "We couldn't verify your email — check your connection and try again.";
}

function VerifyEmailInner() {
  const params = useSearchParams();
  const { refresh } = useAuth();
  const token = params.get("token") ?? "";
  const [state, setState] = useState<"working" | "success" | "error">("working");
  const [message, setMessage] = useState("");
  // React 18 StrictMode double-runs effects in dev; a second POST would burn
  // the single-use token and report a false failure.
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    if (!token) {
      setState("error");
      setMessage("This link is missing its token — use the button in your email.");
      return;
    }
    verifyEmail(token)
      .then(async () => {
        // Refetch /me so a signed-in session's verify banner clears on the
        // client-side nav back into the app (no full reload needed). The
        // page-load getMe races this POST, so its result may be stale.
        await refresh();
        setState("success");
      })
      .catch((err) => {
        setState("error");
        setMessage(messageFor(err));
      });
  }, [token, refresh]);

  if (state === "working") {
    return (
      <p className="text-sm text-ink-soft" data-testid="verify-working">
        Confirming your email…
      </p>
    );
  }
  if (state === "error") {
    return (
      <div className="grid gap-4">
        <ErrorNote message={message} testid="verify-error" />
        <Link href="/" className={`justify-self-start ${btnPrimary}`} data-testid="verify-home">
          Back to Sauti
        </Link>
      </div>
    );
  }
  return (
    <div className="grid gap-4" data-testid="verify-success">
      <p className="rounded-btn border border-line bg-card px-4 py-3 text-sm text-ink-soft">
        Murakoze! Your email is verified — your account is fully set up.
      </p>
      <Link href="/" className={`justify-self-start ${btnPrimary}`} data-testid="verify-home">
        Continue to Sauti
      </Link>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-12">
      <div className="flex items-center gap-[9px]">
        <svg width="24" height="13" viewBox="0 0 24 13" aria-hidden>
          <path d="M0 13 L6 0 L12 13 Z" fill="#C2551A" />
          <path d="M12 13 L18 0 L24 13 Z" fill="#D99A2B" />
        </svg>
        <span className="ky text-[23px] font-bold tracking-[-0.01em]">sauti</span>
      </div>
      <p className="mt-2 text-[10px] tracking-[0.14em] text-ink-faint uppercase">
        Speak it as it&rsquo;s spoken
      </p>
      <h1 className="ky mt-8 text-[28px] font-semibold tracking-[-0.01em]">
        Verifying your email
      </h1>
      <div className="mt-6">
        <Suspense>
          <VerifyEmailInner />
        </Suspense>
      </div>
    </div>
  );
}
