"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getCourses, login, register } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth";
import { btnPrimary, ErrorNote } from "@/components/ui";
import { validateEmail, validatePassword } from "@/lib/validate";
import type { CourseCode } from "@/lib/api/types";

const FALLBACK_COURSES = [
  { code: "KIN" as const, name: "Ikinyarwanda", available: true },
  { code: "SWA" as const, name: "Kiswahili", available: false },
  { code: "FRA" as const, name: "Français", available: false },
];

const PACE_OPTIONS = [
  { hours: 2, label: "2 h", sub: "gentle" },
  { hours: 5, label: "5 h", sub: "steady" },
  { hours: 8, label: "8 h", sub: "immersed" },
];

const labelClass = "text-[11px] font-bold tracking-[0.13em] text-ink-soft uppercase";

const inputClass = (invalid: boolean) =>
  `rounded-btn border bg-card px-4 py-3 text-[15px] outline-none focus:border-accent ${
    invalid ? "border-ember" : "border-line-strong"
  }`;

export default function RegisterPage() {
  const router = useRouter();
  const { refresh } = useAuth();
  const coursesQuery = useQuery({ queryKey: ["courses"], queryFn: getCourses, retry: 1 });

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [courseCode, setCourseCode] = useState<CourseCode>("KIN");
  const [pace, setPace] = useState(5);
  const [touched, setTouched] = useState({ email: false, password: false });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const emailError = validateEmail(email);
  const passwordError = validatePassword(password);
  const formValid = !emailError && !passwordError;

  const courses =
    coursesQuery.data && coursesQuery.data.length > 0
      ? coursesQuery.data
      : FALLBACK_COURSES;

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formValid) {
      setTouched({ email: true, password: true });
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await register({ email, password, course_code: courseCode, pace_hours_week: pace });
      await login({ email, password });
      await refresh();
      router.replace("/placement");
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 409
          ? "That email already has an account — sign in instead."
          : err instanceof ApiError
            ? err.message
            : "We couldn't create your account — check your connection and try again.",
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
        Start speaking, properly.
      </h1>
      <p className="mt-2 text-sm text-ink-soft">
        Pick a language and a weekly rhythm. One rest day never resets you.
      </p>

      <form onSubmit={onSubmit} className="mt-8 grid gap-5" data-testid="register-form">
        {error ? <ErrorNote message={error} testid="register-error" /> : null}

        <fieldset>
          <legend className={labelClass}>Course</legend>
          <div className="mt-2 grid gap-2">
            {courses.map((c) => {
              const selected = c.code === courseCode;
              return (
                <button
                  key={c.code}
                  type="button"
                  data-testid={`course-${c.code}`}
                  onClick={() => setCourseCode(c.code)}
                  className={`flex cursor-pointer items-center justify-between rounded-btn border-[1.5px] px-4 py-3 text-left transition-colors ${
                    selected
                      ? "border-accent bg-accent-soft"
                      : "border-line bg-card hover:border-accent"
                  }`}
                >
                  <span className="ky text-lg">{c.name}</span>
                  <span
                    className={`font-mono text-[10px] uppercase ${
                      selected ? "text-accent" : "text-ink-faint"
                    }`}
                  >
                    {c.available ? (selected ? "chosen" : "full course") : "early · A1 only"}
                  </span>
                </button>
              );
            })}
          </div>
        </fieldset>

        <fieldset>
          <legend className={labelClass}>Weekly pace</legend>
          <div className="mt-2 grid grid-cols-3 gap-2">
            {PACE_OPTIONS.map((p) => (
              <button
                key={p.hours}
                type="button"
                data-testid={`pace-${p.hours}`}
                onClick={() => setPace(p.hours)}
                className={`cursor-pointer rounded-btn border-[1.5px] px-3 py-3 text-center transition-colors ${
                  pace === p.hours
                    ? "border-accent bg-accent-soft"
                    : "border-line bg-card hover:border-accent"
                }`}
              >
                <span className="block font-semibold">{p.label}</span>
                <span className="block text-xs text-ink-soft">{p.sub}</span>
              </button>
            ))}
          </div>
          <p className="mt-2 text-xs text-ink-soft">
            At 5 h a week most learners reach conversational (B1) in about a year.
          </p>
        </fieldset>

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
            data-testid="register-email"
            className={inputClass(touched.email && !!emailError)}
          />
          {touched.email && emailError ? (
            <span className="text-xs text-accent" data-testid="register-email-error">
              {emailError}
            </span>
          ) : null}
        </label>
        <label className="grid gap-1.5">
          <span className={labelClass}>Password</span>
          <input
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
            placeholder="At least 8 characters"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onBlur={() => setTouched((t) => ({ ...t, password: true }))}
            aria-invalid={touched.password && !!passwordError}
            data-testid="register-password"
            className={inputClass(touched.password && !!passwordError)}
          />
          {touched.password && passwordError ? (
            <span className="text-xs text-accent" data-testid="register-password-error">
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
          disabled={busy || (!formValid && (touched.email || touched.password))}
          data-testid="register-submit"
          className={`mt-1 ${btnPrimary}`}
        >
          {busy ? "Creating your account…" : "Create account"}
        </button>
      </form>

      <p className="mt-6 text-sm text-ink-soft">
        Already learning?{" "}
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
