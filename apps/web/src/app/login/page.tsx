"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { login } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth";
import { ErrorNote } from "@/components/ui";
import { validateEmail, validateLoginPassword } from "@/lib/validate";

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
        <span className="text-xs font-semibold tracking-[0.14em] text-ink-soft uppercase">
          Email
        </span>
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
          className={`rounded-xl border bg-card px-4 py-3 outline-none placeholder:text-ink-soft/50 focus:border-accent ${
            touched.email && emailError ? "border-red-400" : "border-line"
          }`}
        />
        {touched.email && emailError ? (
          <span className="text-xs text-red-600" data-testid="login-email-error">
            {emailError}
          </span>
        ) : null}
      </label>
      <label className="grid gap-1.5">
        <span className="text-xs font-semibold tracking-[0.14em] text-ink-soft uppercase">
          Password
        </span>
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
          className={`rounded-xl border bg-card px-4 py-3 outline-none placeholder:text-ink-soft/50 focus:border-accent ${
            touched.password && passwordError ? "border-red-400" : "border-line"
          }`}
        />
        {touched.password && passwordError ? (
          <span className="text-xs text-red-600" data-testid="login-password-error">
            {passwordError}
          </span>
        ) : null}
      </label>
      <button
        type="submit"
        disabled={busy || (!formValid && (touched.email || touched.password))}
        data-testid="login-submit"
        className="mt-2 rounded-full bg-accent px-6 py-3 font-medium text-paper transition-colors hover:bg-accent-deep disabled:opacity-60"
      >
        {busy ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}

export default function LoginPage() {
  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-12">
      <p className="ky text-2xl font-semibold tracking-tight">sauti</p>
      <p className="mt-1 text-[11px] tracking-[0.18em] text-ink-soft uppercase">
        Speak it as it&rsquo;s spoken
      </p>
      <h1 className="ky mt-8 text-3xl font-semibold">Murakaza neza — welcome back.</h1>
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
        <Link href="/register" className="text-accent-deep underline underline-offset-2" data-testid="to-register">
          Create an account
        </Link>
      </p>
    </div>
  );
}
