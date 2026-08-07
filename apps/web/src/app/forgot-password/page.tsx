"use client";

import Link from "next/link";
import { useState } from "react";
import { forgotPassword } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { btnPrimary, ErrorNote } from "@/components/ui";
import { validateEmail } from "@/lib/validate";

const inputClass = (invalid: boolean) =>
  `rounded-btn border bg-card px-4 py-3 text-[15px] outline-none focus:border-accent ${
    invalid ? "border-ember" : "border-line-strong"
  }`;

const labelClass = "text-[11px] font-bold tracking-[0.13em] text-ink-soft uppercase";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [touched, setTouched] = useState(false);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const emailError = validateEmail(email);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (emailError) {
      setTouched(true);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await forgotPassword(email);
      setDone(true);
    } catch (err) {
      // The API never reveals whether the account exists; only rate limits
      // or connectivity can land here.
      setError(
        err instanceof ApiError && err.status === 429
          ? "Too many reset requests — wait a minute and try again."
          : "We couldn't send the email — check your connection and try again.",
      );
      setBusy(false);
    }
  };

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
        Forgot your password?
      </h1>
      <p className="mt-2 text-sm text-ink-soft">
        Tell us your email and we&rsquo;ll send a link to choose a new one.
      </p>

      <div className="mt-8">
        {done ? (
          <p
            className="rounded-btn border border-line bg-card px-4 py-3 text-sm text-ink-soft"
            data-testid="forgot-done"
          >
            Check your inbox — if that address has a Sauti account, a reset link
            is on its way. It works for one hour.
          </p>
        ) : (
          <form onSubmit={onSubmit} className="grid gap-4" data-testid="forgot-form">
            {error ? <ErrorNote message={error} testid="forgot-error" /> : null}
            <label className="grid gap-1.5">
              <span className={labelClass}>Email</span>
              <input
                type="email"
                required
                autoComplete="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onBlur={() => setTouched(true)}
                aria-invalid={touched && !!emailError}
                data-testid="forgot-email"
                className={inputClass(touched && !!emailError)}
              />
              {touched && emailError ? (
                <span className="text-xs text-accent" data-testid="forgot-email-error">
                  {emailError}
                </span>
              ) : null}
            </label>
            <button
              type="submit"
              disabled={busy || (touched && !!emailError)}
              data-testid="forgot-submit"
              className={`mt-2 ${btnPrimary}`}
            >
              {busy ? "Sending…" : "Email me a reset link"}
            </button>
          </form>
        )}
      </div>

      <p className="mt-6 text-sm text-ink-soft">
        Remembered it?{" "}
        <Link
          href="/login"
          className="font-semibold text-accent transition-colors hover:text-accent-deep"
          data-testid="to-login"
        >
          Sign in
        </Link>
      </p>
    </div>
  );
}
