"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { getProgress, getRoadmap, getSessionToday } from "@/lib/api/endpoints";
import { greetingName, useAuth } from "@/lib/auth";
import { consistencyLabel, sessionPlanView } from "@/lib/session-plan";
import { proverbOfTheDay } from "@/lib/proverbs";
import { Card, ErrorNote, Kicker, LoadingNote, VoiceCredit } from "@/components/ui";

function todayLabel(): string {
  return new Date().toLocaleDateString("en-GB", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
}

function greetingWord(): string {
  const h = new Date().getHours();
  if (h < 12) return "Mwaramutse"; // good morning
  if (h < 18) return "Mwiriwe"; // good afternoon
  return "Muraho"; // hello
}

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

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Kicker>{todayLabel()}</Kicker>
          <h1 className="ky mt-1 text-3xl font-semibold tracking-tight sm:text-4xl" data-testid="greeting">
            {greetingWord()}, {greetingName(me)}.
          </h1>
          <p className="mt-2 max-w-md text-ink-soft">
            Your {plan ? `${plan.totalMin}-minute` : "25-minute"} session is ready —{" "}
            {plan?.blockCountLabel ?? "three short blocks"}, then you&rsquo;re done.
          </p>
        </div>
        <VoiceCredit name="Diane" />
      </div>

      <Card testid="session-card">
        {session.isPending ? (
          <LoadingNote label="Planning today's session…" />
        ) : session.isError ? (
          <ErrorNote message="Today's session couldn't load. Refresh to try again." testid="session-error" />
        ) : plan ? (
          <>
            <div className="grid gap-3 sm:grid-cols-3">
              {plan.blocks.map((b, i) => (
                <Link
                  key={i}
                  href={b.href}
                  data-testid="session-block"
                  className="group rounded-xl border border-line bg-paper p-4 transition-colors hover:border-accent"
                >
                  <div className="flex items-baseline justify-between">
                    <span className="text-[10px] font-semibold tracking-[0.16em] text-accent-deep uppercase">
                      {b.tag}
                    </span>
                    <span className="text-xs text-ink-soft">{b.mins} min</span>
                  </div>
                  <p className="ky mt-2 text-lg leading-snug">{b.title}</p>
                  <p className="mt-1 text-sm text-ink-soft">{b.sub}</p>
                </Link>
              ))}
            </div>
            <div className="mt-5 flex items-center justify-between gap-4">
              <p className="text-xs text-ink-soft">
                ≈ {plan.totalMin} minutes, weighted to your weakest skill.
              </p>
              <Link
                href={plan.startHref}
                data-testid="start-session"
                className="rounded-full bg-accent px-6 py-3 font-medium text-paper transition-colors hover:bg-accent-deep"
              >
                Start session
              </Link>
            </div>
          </>
        ) : null}
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        <Card testid="where-you-are">
          <Kicker>Where you are</Kicker>
          {roadmap.isPending ? (
            <LoadingNote />
          ) : current ? (
            <>
              <p className="ky mt-3 text-xl">
                {current.cefr} · {current.unit_ord ? `Unit ${current.unit_ord} — ` : ""}
                {current.unit_title}
              </p>
              {eta ? (
                <p className="mt-2 text-sm text-ink-soft" data-testid="eta">
                  At {eta.pace_hours_week} h a week you reach conversational ({eta.target_cefr}) by{" "}
                  <span className="font-medium text-ink">
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
                className="mt-4 inline-block text-sm text-accent-deep underline underline-offset-2"
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
                className="mt-4 inline-block text-sm text-accent-deep underline underline-offset-2"
              >
                Find your level →
              </Link>
            </>
          )}
        </Card>

        <Card testid="consistency-card">
          <Kicker>Consistency</Kicker>
          {progress.isPending ? (
            <LoadingNote />
          ) : consistency ? (
            <p className="ky mt-3 text-xl" data-testid="consistency">
              {consistencyLabel(consistency.active_days, consistency.window_days)}
            </p>
          ) : (
            <p className="ky mt-3 text-xl">Day one — welcome.</p>
          )}
          <p className="mt-2 text-sm text-ink-soft">
            Rhythm beats streaks — one rest day never resets you.
          </p>
        </Card>
      </div>

      <Card testid="proverb-card" className="bg-cream">
        <p className="ky text-xl">{proverb.ky}</p>
        <p className="mt-1 text-sm text-ink-soft">
          &ldquo;{proverb.en}&rdquo; · proverb of the day
        </p>
      </Card>
    </div>
  );
}
