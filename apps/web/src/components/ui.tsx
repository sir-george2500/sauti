import type { ReactNode } from "react";

/** Small shared presentational atoms — Tailwind only, no component library. */

export function Card({
  children,
  className = "",
  testid,
}: {
  children: ReactNode;
  className?: string;
  testid?: string;
}) {
  return (
    <section
      data-testid={testid}
      className={`rounded-2xl border border-line bg-card p-5 shadow-card sm:p-6 ${className}`}
    >
      {children}
    </section>
  );
}

export function Kicker({ children }: { children: ReactNode }) {
  return (
    <p className="text-[11px] font-semibold tracking-[0.18em] text-ink-soft uppercase">
      {children}
    </p>
  );
}

export function PageTitle({ children }: { children: ReactNode }) {
  return (
    <h1 className="ky mt-1 text-3xl font-semibold tracking-tight sm:text-4xl">{children}</h1>
  );
}

export function VoiceCredit({ name, place = "Kigali voice" }: { name: string; place?: string }) {
  return (
    <span
      className="inline-flex items-center gap-2 rounded-full border border-line bg-cream px-3 py-1 text-[10px] font-semibold tracking-[0.16em] uppercase"
      data-testid="voice-credit"
    >
      <span className="text-accent">●</span> {name}
      <span className="font-normal text-ink-soft">{place}</span>
    </span>
  );
}

export function ErrorNote({ message, testid = "error" }: { message: string; testid?: string }) {
  return (
    <p
      data-testid={testid}
      role="alert"
      className="rounded-xl border border-accent/30 bg-accent-soft px-4 py-3 text-sm text-accent-deep"
    >
      {message}
    </p>
  );
}

export function LoadingNote({ label = "Loading…" }: { label?: string }) {
  return (
    <p className="py-10 text-center text-sm text-ink-soft" data-testid="loading">
      {label}
    </p>
  );
}
