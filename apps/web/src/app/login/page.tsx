"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { login } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth";
import { btnPrimary, ErrorNote } from "@/components/ui";
import { validateEmail, validateLoginPassword } from "@/lib/validate";

const inputClass = (invalid: boolean) =>
  `rounded-btn border bg-card px-4 py-3 text-[15px] outline-none focus:border-accent ${
    invalid ? "border-ember" : "border-line-strong"
  }`;

const labelClass = "text-[11px] font-bold tracking-[0.13em] text-ink-soft uppercase";

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const { refresh } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [touched, setTouched] = useState({ email: false, password: false });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const emailError = validateEmail(email);
  const passwordError = validateLoginPassword(password);
  const formValid = !emailError && !passwordError;

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formValid) {
      setTouched({ email: true, password: true });
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await login({ email, password });
      await refresh();
      // Only follow same-app paths: "/x" but not "//evil.com" or "https://…"
      // (open-redirect guard on the ?next= param).
      const next = params.get("next");
      router.replace(next && next.startsWith("/") && !next.startsWith("//") ? next : "/");
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 401
          ? "That email and password don't match. Try again."
          : "We couldn't sign you in — check your connection and try again.",
      );
      setBusy(false);
    }
  };

  return (
    <form onSubmit={onSubmit} className="grid gap-4" data-testid="login-form">
      {error ? <ErrorNote message={error} testid="login-error" /> : null}
      <label className="grid gap-1.5">
        <span className={labelClass}>Email</span>
        <input
          type="email"
          required
          autoComplete="email"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          onBlur={() => setTouched((t) => ({ ...t, email: true }))}
          aria-invalid={touched.email && !!emailError}
          data-testid="login-email"
          className={inputClass(touched.email && !!emailError)}
        />
        {touched.email && emailError ? (
          <span className="text-xs text-accent" data-testid="login-email-error">
            {emailError}
          </span>
        ) : null}
      </label>
      <label className="grid gap-1.5">
        <span className={labelClass}>Password</span>
        <input
          type="password"
          required
          autoComplete="current-password"
          placeholder="Your password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onBlur={() => setTouched((t) => ({ ...t, password: true }))}
          aria-invalid={touched.password && !!passwordError}
          data-testid="login-password"
          className={inputClass(touched.password && !!passwordError)}
        />
        {touched.password && passwordError ? (
          <span className="text-xs text-accent" data-testid="login-password-error">
            {passwordError}
          </span>
        ) : null}
      </label>
      <button
        type="submit"
        disabled={busy || (!formValid && (touched.email || touched.password))}
        data-testid="login-submit"
        className={`mt-2 ${btnPrimary}`}
      >
        {busy ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}

export default function LoginPage() {
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
        Murakaza neza — welcome back.
      </h1>
      <p className="mt-2 text-sm text-ink-soft">
        Your session is waiting. Rhythm beats streaks — pick up where you left off.
      </p>
      <div className="mt-8">
        <Suspense>
          <LoginForm />
        </Suspense>
      </div>
      <p className="mt-6 text-sm text-ink-soft">
        New here?{" "}
        <Link
          href="/register"
          className="font-semibold text-accent transition-colors hover:text-accent-deep"
          data-testid="to-register"
        >
          Create an account
        </Link>
      </p>
    </div>
  );
}
