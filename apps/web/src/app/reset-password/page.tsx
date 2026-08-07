"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { resetPassword } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { btnPrimary, ErrorNote } from "@/components/ui";
import { validatePassword } from "@/lib/validate";

const inputClass = (invalid: boolean) =>
  `rounded-btn border bg-card px-4 py-3 text-[15px] outline-none focus:border-accent ${
    invalid ? "border-ember" : "border-line-strong"
  }`;

const labelClass = "text-[11px] font-bold tracking-[0.13em] text-ink-soft uppercase";

function messageFor(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.code === "TOKEN_USED")
      return "This reset link was already used — request a new one below.";
    if (err.code === "TOKEN_EXPIRED")
      return "This reset link has expired — request a new one below.";
    if (err.code === "WEAK_PASSWORD")
      return "That password is too common — pick something more personal.";
    if (err.status === 400 || err.status === 422)
      return "This reset link isn't valid — request a new one below.";
    if (err.status === 429)
      return "Too many attempts — wait a minute and try again.";
  }
  return "We couldn't reset your password — check your connection and try again.";
}

function ResetPasswordForm() {
  const params = useSearchParams();
  const token = params.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [touched, setTouched] = useState(false);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const passwordError = validatePassword(password);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (passwordError) {
      setTouched(true);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await resetPassword(token, password);
      setDone(true);
    } catch (err) {
      setError(messageFor(err));
      setBusy(false);
    }
  };

  if (!token) {
    return (
      <div className="grid gap-4">
        <ErrorNote
          message="This link is missing its token — use the button in your email."
          testid="reset-error"
        />
        <Link
          href="/forgot-password"
          className={`justify-self-start ${btnPrimary}`}
          data-testid="reset-request-new"
        >
          Request a new link
        </Link>
      </div>
    );
  }

  if (done) {
    return (
      <div className="grid gap-4" data-testid="reset-success">
        <p className="rounded-btn border border-line bg-card px-4 py-3 text-sm text-ink-soft">
          Your password is changed and every device has been signed out. Sign in
          with the new one.
        </p>
        <Link
          href="/login"
          className={`justify-self-start ${btnPrimary}`}
          data-testid="reset-login-link"
        >
          Sign in
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="grid gap-4" data-testid="reset-form">
      {error ? (
        <div className="grid gap-2">
          <ErrorNote message={error} testid="reset-error" />
          <Link
            href="/forgot-password"
            className="text-sm font-semibold text-accent transition-colors hover:text-accent-deep"
            data-testid="reset-request-new"
          >
            Request a new link
          </Link>
        </div>
      ) : null}
      <label className="grid gap-1.5">
        <span className={labelClass}>New password</span>
        <input
          type="password"
          required
          minLength={8}
          autoComplete="new-password"
          placeholder="At least 8 characters"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onBlur={() => setTouched(true)}
          aria-invalid={touched && !!passwordError}
          data-testid="reset-password"
          className={inputClass(touched && !!passwordError)}
        />
        {touched && passwordError ? (
          <span className="text-xs text-accent" data-testid="reset-password-error">
            {passwordError}
          </span>
        ) : (
          <span className="text-xs text-ink-faint">
            At least 8 characters — avoid the obvious ones.
          </span>
        )}
      </label>
      <button
        type="submit"
        disabled={busy || (touched && !!passwordError)}
        data-testid="reset-submit"
        className={`mt-2 ${btnPrimary}`}
      >
        {busy ? "Saving…" : "Set new password"}
      </button>
    </form>
  );
}

export default function ResetPasswordPage() {
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
        Choose a new password
      </h1>
      <p className="mt-2 text-sm text-ink-soft">
        Changing it signs you out everywhere — you&rsquo;ll sign back in once.
      </p>
      <div className="mt-8">
        <Suspense>
          <ResetPasswordForm />
        </Suspense>
      </div>
    </div>
  );
}
