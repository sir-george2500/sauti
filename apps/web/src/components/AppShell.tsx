"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { RequireAuth, useAuth } from "@/lib/auth";

const NAV = [
  { href: "/", label: "Today", testid: "nav-today" },
  { href: "/roadmap", label: "Roadmap", testid: "nav-roadmap" },
  { href: "/vocab", label: "Vocabulary", testid: "nav-vocab" },
  { href: "/progress", label: "Progress", testid: "nav-progress" },
] as const;

const COURSES = [
  { code: "KIN", label: "Ikinyarwanda" },
  { code: "SWA", label: "Kiswahili" },
  { code: "FRA", label: "Français" },
] as const;

function LanguageSwitcher() {
  const { me } = useAuth();
  const active = me?.profile?.course_code ?? "KIN";
  return (
    <div className="hidden items-center gap-1.5 md:flex" data-testid="language-switcher">
      {COURSES.map((c) => {
        const isActive = c.code === active;
        return (
          <span
            key={c.code}
            className={
              isActive
                ? "rounded-full bg-ink px-3 py-1 text-xs font-medium text-paper"
                : "rounded-full border border-line px-3 py-1 text-xs text-ink-soft"
            }
            title={isActive ? `${c.label} — active course` : `${c.label} — joinable`}
          >
            {c.label}
            {!isActive && <span className="ml-1 text-accent">+</span>}
          </span>
        );
      })}
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { signOut } = useAuth();

  return (
    <RequireAuth>
      <div className="min-h-screen">
        <header className="sticky top-0 z-20 border-b border-line bg-paper/90 backdrop-blur">
          <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
            <Link href="/" className="flex items-baseline gap-2" data-testid="nav-home">
              <span className="ky text-xl font-semibold tracking-tight">sauti</span>
              <span className="hidden text-[11px] tracking-[0.18em] text-ink-soft uppercase sm:inline">
                Speak it as it&rsquo;s spoken
              </span>
            </Link>
            <LanguageSwitcher />
            <button
              type="button"
              data-testid="sign-out"
              onClick={async () => {
                await signOut();
                router.replace("/login");
              }}
              className="text-xs text-ink-soft transition-colors hover:text-accent"
            >
              Sign out
            </button>
          </div>
          <nav className="mx-auto flex max-w-5xl gap-1 overflow-x-auto px-3 pb-2 sm:px-5">
            {NAV.map((item) => {
              const active =
                item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  data-testid={item.testid}
                  className={
                    active
                      ? "rounded-full bg-accent-soft px-3.5 py-1.5 text-sm font-medium text-accent-deep"
                      : "rounded-full px-3.5 py-1.5 text-sm text-ink-soft transition-colors hover:text-ink"
                  }
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </header>
        <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 sm:py-10">{children}</main>
        <footer className="mx-auto max-w-5xl px-4 pb-10 sm:px-6">
          <p className="text-[11px] tracking-[0.14em] text-ink-soft uppercase">
            Sauti · Rhythm beats streaks
          </p>
        </footer>
      </div>
    </RequireAuth>
  );
}
