"use client";

import { useQuery } from "@tanstack/react-query";
import { getProgress } from "@/lib/api/endpoints";
import { consistencyLabel } from "@/lib/session-plan";
import { Card, ErrorNote, Kicker, LoadingNote, PageTitle } from "@/components/ui";

const SKILL_LABELS: Record<string, string> = {
  listening: "Listening",
  speaking: "Speaking",
  reading: "Reading",
  writing: "Writing",
};

export default function ProgressPage() {
  const progress = useQuery({ queryKey: ["progress"], queryFn: getProgress });

  if (progress.isPending) return <LoadingNote label="Measuring the road…" />;
  if (progress.isError) return <ErrorNote message="Progress couldn't load. Refresh to try again." />;

  const data = progress.data;
  const eta = data.eta;

  return (
    <div className="grid gap-6">
      <div>
        <Kicker>Track · Progress</Kicker>
        <PageTitle>Your road to {eta?.target_cefr ?? "B1"}.</PageTitle>
        <p className="mt-2 max-w-lg text-ink-soft">
          Measured against CEFR can-do standards — not points.
          {eta ? (
            <>
              {" "}
              On pace for{" "}
              <span className="font-medium text-ink">
                {new Date(eta.eta_date).toLocaleDateString("en-GB", {
                  month: "long",
                  year: "numeric",
                })}
              </span>
              .
            </>
          ) : null}
        </p>
      </div>

      <Card testid="skill-balance">
        <h2 className="ky text-xl font-semibold">Skill balance</h2>
        <div className="mt-4 grid gap-4">
          {data.skills.map((s) => (
            <div key={s.skill} data-testid={`skill-${s.skill}`}>
              <div className="flex items-baseline justify-between">
                <span className="text-sm font-medium">{SKILL_LABELS[s.skill] ?? s.skill}</span>
                <span className="text-xs font-semibold tracking-widest text-accent-deep uppercase">
                  {s.cefr}
                </span>
              </div>
              <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-cream">
                <div
                  className="h-full rounded-full bg-accent"
                  style={{ width: `${Math.round(Math.min(1, Math.max(0, s.pct)) * 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
        <p className="mt-4 text-sm text-ink-soft">
          The daily session leans toward whichever bar lags — no extra planning needed.
        </p>
      </Card>

      <Card testid="cando-checklist">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="ky text-xl font-semibold">Can-do statements</h2>
          <p className="text-sm text-ink-soft" data-testid="cando-count">
            {data.cando.confirmed} of {data.cando.total} confirmed in live speaking checks
          </p>
        </div>
        <ul className="mt-4 grid gap-2">
          {data.cando.items.map((cd) => (
            <li
              key={cd.id}
              data-testid="cando-item"
              className="flex items-start gap-3 rounded-xl border border-line bg-paper px-4 py-3"
            >
              <span
                aria-hidden
                className={cd.status === "confirmed" ? "text-accent-deep" : "text-ink-soft"}
              >
                {cd.status === "confirmed" ? "✓" : "○"}
              </span>
              <div className="min-w-0">
                <p className="text-sm leading-relaxed">{cd.text}</p>
                <p className="mt-0.5 text-[10px] font-semibold tracking-[0.14em] text-ink-soft uppercase">
                  {cd.cefr} · {cd.skill}
                </p>
              </div>
            </li>
          ))}
        </ul>
      </Card>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card testid="total-time">
          <Kicker>Total time</Kicker>
          <p className="ky mt-2 text-3xl font-semibold">{data.totals.hours_total} h</p>
        </Card>
        <Card testid="weekly-average">
          <Kicker>Weekly average</Kicker>
          <p className="ky mt-2 text-3xl font-semibold">{data.totals.weekly_avg_hours} h</p>
        </Card>
        <Card testid="sentences-spoken">
          <Kicker>Sentences spoken</Kicker>
          <p className="ky mt-2 text-3xl font-semibold">{data.totals.sentences_spoken}</p>
        </Card>
      </div>

      <Card testid="consistency-progress" className="bg-cream">
        <Kicker>Consistency</Kicker>
        <p className="ky mt-2 text-xl">
          {consistencyLabel(data.consistency.active_days, data.consistency.window_days)}
        </p>
        <p className="mt-1 text-sm text-ink-soft">
          Rhythm beats streaks — one rest day never resets you.
        </p>
      </Card>
    </div>
  );
}
