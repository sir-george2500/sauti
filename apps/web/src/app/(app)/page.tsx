"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { getProgress, getRoadmap, getSessionToday } from "@/lib/api/endpoints";
import { greetingName, useAuth } from "@/lib/auth";
import { consistencyLabel, sessionPlanView } from "@/lib/session-plan";
import { proverbOfTheDay } from "@/lib/proverbs";
import { DailyTimer } from "@/components/DailyTimer";
import { btnPrimary, Card, CardLabel, ErrorNote, Kicker, LoadingNote } from "@/components/ui";
import type { SessionBlockKind } from "@/lib/api/types";

const CEFR_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"] as const;

function todayLabel(): string {
  const now = new Date();
  const weekday = now.toLocaleDateString("en-US", { weekday: "long" });
  const month = now.toLocaleDateString("en-US", { month: "long" });
  return `${weekday} · ${month} ${now.getDate()}`;
}

function greetingWord(): string {
  const h = new Date().getHours();
  if (h < 12) return "Mwaramutse"; // good morning
  if (h < 18) return "Mwiriwe"; // good afternoon
  return "Muraho"; // hello
}

const TAG_STYLES: Record<SessionBlockKind, string> = {
  review: "bg-green-soft text-green",
  lesson: "bg-accent-soft text-accent",
  speak: "bg-amber-soft text-amber-text",
};

export default function TodayPage() {
  const { me } = useAuth();
  const session = useQuery({ queryKey: ["session-today"], queryFn: getSessionToday });
  const roadmap = useQuery({ queryKey: ["roadmap"], queryFn: getRoadmap });
  const progress = useQuery({ queryKey: ["progress"], queryFn: getProgress });

  const proverb = proverbOfTheDay();
  const plan = session.data ? sessionPlanView(session.data) : null;
  const current = roadmap.data?.current;
  const eta = roadmap.data?.eta ?? progress.data?.eta ?? null;
  const consistency = progress.data?.consistency;

  // Fraction of the current level completed, from lesson statuses.
  const currentLevel = roadmap.data?.levels.find((l) => l.cefr === current?.cefr);
  const levelLessons = currentLevel?.units.flatMap((u) => u.lessons) ?? [];
  const levelPct =
    levelLessons.length > 0
      ? Math.round(
          (levelLessons.filter((l) => l.status === "done").length / levelLessons.length) * 100,
        )
      : 0;
  const currentIdx = current ? CEFR_LEVELS.indexOf(current.cefr) : 0;

  const windowDays = consistency?.window_days ?? 14;
  const activeDays = consistency?.active_days ?? 0;
  const days = Array.from({ length: windowDays }, (_, i) => ({
    active: i >= windowDays - activeDays,
    today: i === windowDays - 1,
  }));

  return (
    <div className="grid gap-4">
      <div className="mb-2 flex flex-wrap items-end justify-between gap-5">
        <div>
          <Kicker>{todayLabel()}</Kicker>
          <h1
            className="ky mt-2.5 text-[28px] leading-tight font-semibold tracking-[-0.01em] sm:text-[34px]"
            data-testid="greeting"
          >
            {greetingWord()}, {greetingName(me)}.
          </h1>
          <p className="mt-2 text-[15px] text-ink-soft">
            Your {plan ? `${plan.totalMin}-minute` : "25-minute"} session is ready —{" "}
            {plan?.blockCountLabel ?? "three short blocks"}, then you&rsquo;re done.
          </p>
        </div>
        {plan ? (
          <Link href={plan.startHref} data-testid="start-session" className={btnPrimary}>
            Start session
          </Link>
        ) : null}
      </div>

      <div className="grid gap-3.5" data-testid="session-card">
        {session.isPending ? (
          <LoadingNote label="Planning today's session…" />
        ) : session.isError ? (
          <ErrorNote
            message="Today's session couldn't load. Refresh to try again."
            testid="session-error"
          />
        ) : plan ? (
          <>
            <div className="grid gap-3.5 sm:grid-cols-3">
              {plan.blocks.map((b, i) => (
                <Link
                  key={i}
                  href={b.href}
                  data-testid="session-block"
                  className="rounded-card border border-line bg-card p-[18px] shadow-card transition-colors hover:border-accent"
                >
                  <div className="mb-3 flex items-center justify-between">
                    <span
                      className={`rounded-[5px] px-[7px] py-1 text-[10px] font-bold tracking-[0.13em] uppercase ${TAG_STYLES[b.kind]}`}
                    >
                      {b.tag}
                    </span>
                    <span className="font-mono text-[11px] text-ink-soft uppercase">
                      {b.mins} min
                    </span>
                  </div>
                  <p className="text-[15px] leading-[1.3] font-semibold">{b.title}</p>
                  <p className="mt-[5px] text-[12.5px] text-ink-soft">{b.sub}</p>
                </Link>
              ))}
            </div>
            <p className="text-xs text-ink-faint">
              ≈ {plan.totalMin} minutes, weighted to your weakest skill.
            </p>
          </>
        ) : null}
      </div>

      <div className="grid gap-3.5 md:grid-cols-[1.4fr_1fr]">
        <Card testid="where-you-are" className="p-5">
          <CardLabel>Where you are</CardLabel>
          {roadmap.isPending ? (
            <LoadingNote />
          ) : current ? (
            <>
              <div className="mt-3.5 flex gap-[5px]">
                {CEFR_LEVELS.map((label, i) => {
                  const fill = i < currentIdx ? 100 : i === currentIdx ? Math.max(levelPct, 6) : 0;
                  const color = i < currentIdx ? "bg-green" : "bg-accent";
                  const labelColor =
                    i < currentIdx
                      ? "text-green"
                      : i === currentIdx
                        ? "text-accent"
                        : "text-ink-faint";
                  return (
                    <div key={label} className="flex-1">
                      <div className="h-2 overflow-hidden rounded-[4px] bg-track">
                        <div className={`h-full ${color}`} style={{ width: `${fill}%` }} />
                      </div>
                      <p className={`mt-[5px] font-mono text-[10px] ${labelColor}`}>{label}</p>
                    </div>
                  );
                })}
              </div>
              <p className="ky mt-2 text-lg font-semibold">
                {current.cefr} · {current.unit_ord ? `Unit ${current.unit_ord} — ` : ""}
                {current.unit_title}
              </p>
              {eta ? (
                <p className="mt-1.5 text-[13px] text-ink-soft" data-testid="eta">
                  At {eta.pace_hours_week} h a week you reach conversational ({eta.target_cefr}) by{" "}
                  <span className="font-semibold text-green">
                    {new Date(eta.eta_date).toLocaleDateString("en-GB", {
                      month: "long",
                      year: "numeric",
                    })}
                  </span>
                  .
                </p>
              ) : null}
              <Link
                href="/roadmap"
                className="mt-3 inline-block text-[13px] font-semibold text-accent transition-colors hover:text-accent-deep"
                data-testid="to-roadmap"
              >
                See the whole road →
              </Link>
            </>
          ) : (
            <>
              <p className="mt-3 text-sm text-ink-soft">
                No starting point yet — take the placement, or begin at A1.
              </p>
              <Link
                href="/placement"
                className="mt-4 inline-block text-[13px] font-semibold text-accent transition-colors hover:text-accent-deep"
              >
                Find your level →
              </Link>
            </>
          )}
        </Card>

        <Card testid="consistency-card" className="p-5">
          <CardLabel>Consistency</CardLabel>
          {progress.isPending ? (
            <LoadingNote />
          ) : (
            <>
              <div className="mt-3.5 mb-3 grid grid-cols-7 gap-1.5">
                {days.map((d, i) => (
                  <div
                    key={i}
                    className={`h-[22px] rounded-md ${d.active ? "bg-green" : "bg-track"} ${
                      d.today ? "border-2 border-accent" : ""
                    }`}
                  />
                ))}
              </div>
              <p className="text-[13px] text-ink-soft" data-testid="consistency">
                {consistencyLabel(activeDays, windowDays)}
              </p>
              <p className="mt-2.5 rounded-lg bg-amber-soft px-2.5 py-2 text-xs text-amber-text">
                Rhythm beats streaks — one rest day never resets you.
              </p>
            </>
          )}
        </Card>
      </div>

      <DailyTimer />

      <div
        data-testid="proverb-card"
        className="flex items-center gap-[18px] rounded-card bg-bark px-6 py-[22px] text-paper"
      >
        <span
          aria-hidden
          className="flex h-11 w-11 flex-none items-center justify-center rounded-full border-[1.5px] border-gold text-gold"
        >
          <svg viewBox="0 0 16 16" className="ml-0.5 h-3 w-3 fill-current">
            <path d="M4 2.5v11a.6.6 0 0 0 .92.5l8.4-5.5a.6.6 0 0 0 0-1L4.92 2a.6.6 0 0 0-.92.5Z" />
          </svg>
        </span>
        <div className="min-w-0 flex-1">
          <p className="ky text-[21px] italic">{proverb.ky}</p>
          <p className="mt-1 text-[13px] text-bark-mute">
            &ldquo;{proverb.en}&rdquo; · proverb of the day
          </p>
        </div>
        <p className="hidden flex-none text-right font-mono text-[10.5px] leading-[1.6] text-gold uppercase sm:block">
          ● Diane
          <br />
          Kigali voice
        </p>
      </div>
    </div>
  );
}
