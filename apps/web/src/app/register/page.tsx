"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getCourses, login, register } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth";
import { ErrorNote } from "@/components/ui";
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

export default function RegisterPage() {
  const router = useRouter();
  const { refresh } = useAuth();
  const coursesQuery = useQuery({ queryKey: ["courses"], queryFn: getCourses, retry: 1 });

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [courseCode, setCourseCode] = useState<CourseCode>("KIN");
  const [pace, setPace] = useState(5);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const courses =
    coursesQuery.data && coursesQuery.data.length > 0
      ? coursesQuery.data
      : FALLBACK_COURSES;

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
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
      <p className="ky text-2xl font-semibold tracking-tight">sauti</p>
      <p className="mt-1 text-[11px] tracking-[0.18em] text-ink-soft uppercase">
        Speak it as it&rsquo;s spoken
      </p>
      <h1 className="ky mt-8 text-3xl font-semibold">Start speaking, properly.</h1>
      <p className="mt-2 text-sm text-ink-soft">
        Pick a language and a weekly rhythm. One rest day never resets you.
      </p>

      <form onSubmit={onSubmit} className="mt-8 grid gap-5" data-testid="register-form">
        {error ? <ErrorNote message={error} testid="register-error" /> : null}

        <fieldset>
          <legend className="text-xs font-semibold tracking-[0.14em] text-ink-soft uppercase">
            Course
          </legend>
          <div className="mt-2 grid gap-2">
            {courses.map((c) => {
              const selected = c.code === courseCode;
              return (
                <button
                  key={c.code}
                  type="button"
                  data-testid={`course-${c.code}`}
                  onClick={() => setCourseCode(c.code)}
                  className={`flex items-center justify-between rounded-xl border px-4 py-3 text-left transition-colors ${
                    selected
                      ? "border-accent bg-accent-soft"
                      : "border-line bg-card hover:border-accent"
                  }`}
                >
                  <span className="ky text-lg">{c.name}</span>
                  <span className="text-xs text-ink-soft">
                    {c.available ? (selected ? "chosen" : "full course") : "early — A1 only"}
                  </span>
                </button>
              );
            })}
          </div>
        </fieldset>

        <fieldset>
          <legend className="text-xs font-semibold tracking-[0.14em] text-ink-soft uppercase">
            Weekly pace
          </legend>
          <div className="mt-2 grid grid-cols-3 gap-2">
            {PACE_OPTIONS.map((p) => (
              <button
                key={p.hours}
                type="button"
                data-testid={`pace-${p.hours}`}
                onClick={() => setPace(p.hours)}
                className={`rounded-xl border px-3 py-3 text-center transition-colors ${
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
          <span className="text-xs font-semibold tracking-[0.14em] text-ink-soft uppercase">
            Email
          </span>
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            data-testid="register-email"
            className="rounded-xl border border-line bg-card px-4 py-3 outline-none focus:border-accent"
          />
        </label>
        <label className="grid gap-1.5">
          <span className="text-xs font-semibold tracking-[0.14em] text-ink-soft uppercase">
            Password
          </span>
          <input
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            data-testid="register-password"
            className="rounded-xl border border-line bg-card px-4 py-3 outline-none focus:border-accent"
          />
        </label>

        <button
          type="submit"
          disabled={busy}
          data-testid="register-submit"
          className="mt-1 rounded-full bg-accent px-6 py-3 font-medium text-paper transition-colors hover:bg-accent-deep disabled:opacity-60"
        >
          {busy ? "Creating your account…" : "Create account"}
        </button>
      </form>

      <p className="mt-6 text-sm text-ink-soft">
        Already learning?{" "}
        <Link href="/login" className="text-accent-deep underline underline-offset-2" data-testid="to-login">
          Sign in
        </Link>
      </p>
    </div>
  );
}
