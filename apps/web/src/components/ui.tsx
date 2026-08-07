import type { ReactNode } from "react";

/** Small shared presentational atoms — Tailwind only, no component library. */

/** Primary terracotta button — mockup: #B4470B, radius 10, 14/600. */
export const btnPrimary =
  "inline-block cursor-pointer rounded-btn bg-accent px-5 py-3 text-sm font-semibold text-on-accent transition-colors hover:bg-accent-hover disabled:cursor-default disabled:opacity-60";

/** Quiet outlined button — mockup: transparent, #D8CDB6 border, soft ink. */
export const btnGhost =
  "inline-block cursor-pointer rounded-btn border border-line-strong bg-transparent px-4 py-3 text-sm font-semibold text-ink-soft transition-colors hover:border-accent hover:text-accent disabled:cursor-default disabled:opacity-60";

/** Green button — mockup's "Review 8 due" treatment. */
export const btnGreen =
  "inline-block cursor-pointer rounded-btn bg-green px-5 py-3 text-sm font-semibold text-on-accent transition-colors hover:bg-green-hover disabled:cursor-default disabled:opacity-60";

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
      className={`rounded-card border border-line bg-card p-5 shadow-card sm:p-6 ${className}`}
    >
      {children}
    </section>
  );
}

/** Page-level eyebrow: terracotta small caps above the big serif title. */
export function Kicker({ children }: { children: ReactNode }) {
  return (
    <p className="text-[11px] font-bold tracking-[0.14em] text-accent uppercase">
      {children}
    </p>
  );
}

/** Card-level label: quiet small caps inside white cards. */
export function CardLabel({ children }: { children: ReactNode }) {
  return (
    <p className="text-[11px] font-bold tracking-[0.13em] text-ink-soft uppercase">
      {children}
    </p>
  );
}

export function PageTitle({ children }: { children: ReactNode }) {
  return (
    <h1 className="ky mt-2.5 text-[28px] leading-tight font-semibold tracking-[-0.01em] sm:text-[34px]">
      {children}
    </h1>
  );
}

/** Muted lead paragraph under the page title. */
export function Lead({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <p className={`mt-2 text-[15px] text-ink-soft ${className}`}>{children}</p>;
}

export function VoiceCredit({ name, place = "Kigali voice" }: { name: string; place?: string }) {
  return (
    <span
      className="inline-flex flex-col items-end text-right font-mono text-[10.5px] leading-[1.6] text-gold uppercase"
      data-testid="voice-credit"
    >
      <span>● {name}</span>
      <span>{place}</span>
    </span>
  );
}

export function ErrorNote({ message, testid = "error" }: { message: string; testid?: string }) {
  return (
    <p
      data-testid={testid}
      role="alert"
      className="rounded-btn border border-accent-soft-line bg-accent-soft px-4 py-3 text-sm text-accent-deep"
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
