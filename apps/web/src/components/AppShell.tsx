"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  getProgress,
  getRoadmap,
  getScenarios,
  getVocabDecks,
} from "@/lib/api/endpoints";
import { greetingName, RequireAuth, useAuth } from "@/lib/auth";

const COURSES: { code: string; label: string }[] = [
  { code: "KIN", label: "Ikinyarwanda" },
  { code: "SWA", label: "Kiswahili" },
  { code: "FRA", label: "Français" },
];

/** Sidebar data is shared with the pages (same query keys) but kept fresh
 *  for longer — the shell never needs second-by-second accuracy. */
const SHELL_STALE = { staleTime: 300_000 };

/** Progress and vocab-deck data are nice-to-haves in the shell (rhythm pill,
 *  due badge, hour totals). They render from whatever the pages have already
 *  cached but never trigger their own fetch: the API's multi-query endpoints
 *  are expensive against the remote DB, and a hard reload of a lesson page
 *  must spend its bandwidth on the lesson, not sidebar garnish. */
const CACHE_ONLY = { staleTime: Infinity, enabled: false } as const;

function Wordmark() {
  return (
    <div className="px-[26px] pt-[26px] pb-[18px]">
      <Link href="/" data-testid="nav-home" className="flex items-center gap-[9px]">
        <svg width="24" height="13" viewBox="0 0 24 13" aria-hidden>
          <path d="M0 13 L6 0 L12 13 Z" fill="#C2551A" />
          <path d="M12 13 L18 0 L24 13 Z" fill="#D99A2B" />
        </svg>
        <span className="ky text-[23px] font-bold tracking-[-0.01em] text-paper">sauti</span>
      </Link>
      <p className="mt-2 text-[10px] tracking-[0.14em] text-bark-mist uppercase">
        Speak it as it&rsquo;s spoken
      </p>
    </div>
  );
}

function LanguageCard() {
  const { me } = useAuth();
  const roadmap = useQuery({ queryKey: ["roadmap"], queryFn: getRoadmap, ...SHELL_STALE });

  const activeCode = me?.profile?.course_code ?? "KIN";
  const active = COURSES.find((c) => c.code === activeCode) ?? COURSES[0];
  const others = COURSES.filter((c) => c.code !== active.code);
  const current = roadmap.data?.current;
  const level = current?.cefr ?? me?.profile?.placed_level ?? "A1";

  return (
    <div
      className="mx-5 mb-5 rounded-xl border border-bark-line bg-bark-panel px-4 py-3.5"
      data-testid="language-switcher"
    >
      <div className="flex items-baseline justify-between">
        <span className="text-xs font-bold tracking-[0.1em] text-bark-glow uppercase">
          {active.label}
        </span>
        <span className="font-mono text-[11px] text-gold">{level}</span>
      </div>
      <p className="mt-[5px] text-xs text-bark-mute">
        {current
          ? `${current.unit_ord ? `Unit ${current.unit_ord} · ` : ""}${current.unit_title}`
          : "Finding your place…"}
      </p>
      <div className="my-2.5 mt-3 h-px bg-bark-line" />
      <div className="flex flex-col gap-1.5">
        {others.map((c) => (
          <div
            key={c.code}
            className="flex justify-between text-xs text-bark-mist"
            title={`${c.label} — joinable`}
          >
            <span>{c.label}</span>
            <span>+</span>
          </div>
        ))}
      </div>
    </div>
  );
}

interface NavItem {
  label: string;
  href: string;
  testid?: string;
  badge?: string;
  isActive: (path: string) => boolean;
}

function NavRow({ item, pathname }: { item: NavItem; pathname: string }) {
  const active = item.isActive(pathname);
  return (
    <Link
      href={item.href}
      data-testid={item.testid}
      className={`flex items-center gap-2.5 rounded-nav px-3 py-[9px] text-[13.5px] transition-colors ${
        active
          ? "bg-ember/22 font-semibold text-bark-hi"
          : "font-medium text-bark-soft hover:bg-paper/7"
      }`}
    >
      <span
        aria-hidden
        className={`h-[7px] w-[7px] flex-none rounded-[2px] ${active ? "bg-ember" : "bg-bark-dot"}`}
      />
      <span>{item.label}</span>
      {item.badge ? (
        <span className="ml-auto font-mono text-[10px] text-gold">{item.badge}</span>
      ) : null}
    </Link>
  );
}

function SidebarNav() {
  const pathname = usePathname();
  const roadmap = useQuery({ queryKey: ["roadmap"], queryFn: getRoadmap, ...SHELL_STALE });
  const decks = useQuery({ queryKey: ["vocab-decks"], queryFn: getVocabDecks, ...CACHE_ONLY });
  const scenarios = useQuery({ queryKey: ["scenarios"], queryFn: getScenarios, ...SHELL_STALE });

  const current = roadmap.data?.current;
  const lessonId = current?.lesson_id ?? null;
  const lessonBadge =
    current?.unit_ord && current?.lesson_ord ? `${current.unit_ord}.${current.lesson_ord}` : "";
  const totalDue = decks.data?.total_due ?? 0;
  const firstScenario = scenarios.data?.[0]?.id ?? null;
  // First item of the current lesson feeds the pronunciation drill.
  const currentLesson = roadmap.data?.levels
    ?.flatMap((l) => l.units)
    .flatMap((u) => u.lessons)
    .find((l) => l.id === lessonId);
  const firstItemId = currentLesson?.items?.[0]?.id ?? null;

  const sections: { label: string; items: NavItem[] }[] = [
    {
      label: "Learn",
      items: [
        { label: "Today", href: "/", testid: "nav-today", isActive: (p) => p === "/" },
        {
          label: "Roadmap",
          href: "/roadmap",
          testid: "nav-roadmap",
          isActive: (p) => p.startsWith("/roadmap"),
        },
        {
          label: "Lesson",
          href: lessonId ? `/lesson/${lessonId}` : "/roadmap",
          badge: lessonBadge,
          isActive: (p) => p.startsWith("/lesson"),
        },
        {
          label: "Vocabulary",
          href: "/vocab",
          testid: "nav-vocab",
          badge: totalDue > 0 ? String(totalDue) : "",
          isActive: (p) => p.startsWith("/vocab"),
        },
      ],
    },
    {
      label: "Practice",
      items: [
        {
          label: "Conversation",
          href: firstScenario ? `/practice/conversation/${firstScenario}` : "/roadmap",
          isActive: (p) => p.startsWith("/practice/conversation"),
        },
        {
          label: "Pronunciation",
          href: firstItemId ? `/practice/pronunciation/${firstItemId}` : "/roadmap",
          isActive: (p) => p.startsWith("/practice/pronunciation"),
        },
        {
          label: "Listening",
          href: lessonId ? `/practice/listening/${lessonId}` : "/roadmap",
          isActive: (p) => p.startsWith("/practice/listening"),
        },
      ],
    },
    {
      label: "Track",
      items: [
        {
          label: "Progress",
          href: "/progress",
          testid: "nav-progress",
          isActive: (p) => p.startsWith("/progress"),
        },
        {
          label: "Placement",
          href: "/placement",
          isActive: (p) => p.startsWith("/placement"),
        },
      ],
    },
  ];

  return (
    <nav className="flex-1 px-3.5">
      {sections.map((sec) => (
        <div key={sec.label} className="mb-4">
          <p className="mb-1.5 px-3 text-[10px] font-bold tracking-[0.18em] text-bark-faint uppercase">
            {sec.label}
          </p>
          {sec.items.map((item) => (
            <NavRow key={item.label} item={item} pathname={pathname} />
          ))}
        </div>
      ))}
    </nav>
  );
}

function SidebarFooter() {
  const { me, signOut } = useAuth();
  const router = useRouter();
  const progress = useQuery({ queryKey: ["progress"], queryFn: getProgress, ...CACHE_ONLY });

  const gamification = me?.profile?.gamification ?? "light";
  const consistency = progress.data?.consistency;
  const hours = progress.data?.totals?.hours_total;
  const name = greetingName(me);

  return (
    <div className="border-t border-bark-line px-5 pt-[18px] pb-[22px]">
      {gamification === "light" && consistency ? (
        <div className="mb-3 flex items-center gap-2 rounded-full border border-rhythm-line bg-rhythm-bg py-[7px] pr-3 pl-3">
          <span aria-hidden className="animate-rhythm h-2 w-2 rounded-full bg-gold" />
          <span className="text-xs font-semibold text-rhythm-text">
            {consistency.active_days}-day rhythm
          </span>
          <span className="ml-auto font-mono text-[10px] text-bark-mist uppercase">
            Last {consistency.window_days}
          </span>
        </div>
      ) : null}
      <div className="flex items-center gap-2.5">
        <span
          aria-hidden
          className="flex h-8 w-8 flex-none items-center justify-center rounded-full bg-green text-[13px] font-bold text-paper"
        >
          {name.charAt(0).toUpperCase()}
        </span>
        <div className="min-w-0">
          <p className="truncate text-[13px] font-semibold text-paper">{name}</p>
          <p className="text-[11px] text-bark-mist">
            {consistency ? `Day ${consistency.active_days}` : "Day one"}
            {typeof hours === "number" ? ` · ${hours} h total` : ""}
          </p>
        </div>
        <button
          type="button"
          data-testid="sign-out"
          onClick={async () => {
            await signOut();
            router.replace("/login");
          }}
          className="ml-auto cursor-pointer text-[11px] text-bark-mist transition-colors hover:text-bark-glow"
        >
          Sign out
        </button>
      </div>
    </div>
  );
}

function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen bg-paper lg:h-screen lg:overflow-hidden">
      <aside className="hidden w-[252px] flex-none flex-col overflow-y-auto bg-bark text-paper lg:flex">
        <Wordmark />
        <LanguageCard />
        <SidebarNav />
        <SidebarFooter />
      </aside>
      <div className="flex min-w-0 flex-1 flex-col lg:overflow-y-auto">
        <MobileTopBar />
        <main className="mx-auto w-full max-w-[940px] px-5 pt-8 pb-24 sm:px-8 lg:px-12 lg:pt-[46px]">
          {children}
        </main>
      </div>
    </div>
  );
}

/** Compact bark-coloured bar for < lg screens; testids live on the sidebar
 *  only, so every data-testid stays unique in the DOM. */
function MobileTopBar() {
  const pathname = usePathname();
  const links = [
    { label: "Today", href: "/", active: pathname === "/" },
    { label: "Roadmap", href: "/roadmap", active: pathname.startsWith("/roadmap") },
    { label: "Vocabulary", href: "/vocab", active: pathname.startsWith("/vocab") },
    { label: "Progress", href: "/progress", active: pathname.startsWith("/progress") },
  ];
  return (
    <header className="sticky top-0 z-20 bg-bark text-paper lg:hidden">
      <div className="flex items-center justify-between px-5 py-3">
        <Link href="/" className="flex items-center gap-2">
          <svg width="20" height="11" viewBox="0 0 24 13" aria-hidden>
            <path d="M0 13 L6 0 L12 13 Z" fill="#C2551A" />
            <path d="M12 13 L18 0 L24 13 Z" fill="#D99A2B" />
          </svg>
          <span className="ky text-lg font-bold text-paper">sauti</span>
        </Link>
        <nav className="flex gap-1 overflow-x-auto">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`rounded-nav px-2.5 py-1.5 text-[13px] whitespace-nowrap ${
                l.active ? "bg-ember/22 font-semibold text-bark-hi" : "text-bark-soft"
              }`}
            >
              {l.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <RequireAuth>
      <Shell>{children}</Shell>
    </RequireAuth>
  );
}
