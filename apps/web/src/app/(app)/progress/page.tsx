"use client";

import { useQuery } from "@tanstack/react-query";
import { getProgress } from "@/lib/api/endpoints";
import { consistencyLabel } from "@/lib/session-plan";
import { Card, CardLabel, ErrorNote, Kicker, Lead, LoadingNote, PageTitle } from "@/components/ui";

const SKILL_LABELS: Record<string, string> = {
  listening: "Listening",
  speaking: "Speaking",
  reading: "Reading",
  writing: "Writing",
};

const CEFR_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"] as const;

export default function ProgressPage() {
  const progress = useQuery({ queryKey: ["progress"], queryFn: getProgress });

  if (progress.isPending) return <LoadingNote label="Measuring the road…" />;
  if (progress.isError) return <ErrorNote message="Progress couldn't load. Refresh to try again." />;

  const data = progress.data;
  const eta = data.eta;

  // Rough overall position: the modal CEFR of the four skill estimates.
  const skillLevels = data.skills.map((s) => CEFR_LEVELS.indexOf(s.cefr));
  const currentIdx = skillLevels.length > 0 ? Math.max(0, Math.min(...skillLevels)) : 0;
  const withinPct = Math.round(
    (data.skills.reduce((acc, s) => acc + Math.min(1, Math.max(0, s.pct)), 0) /
      Math.max(1, data.skills.length)) *
      100,
  );

  return (
    <div className="grid gap-3.5">
      <div className="mb-2">
        <Kicker>Track · Progress</Kicker>
        <PageTitle>Your road to {eta?.target_cefr ?? "B1"}.</PageTitle>
        <Lead className="max-w-lg">
          Measured against CEFR can-do standards — not points.
          {eta ? (
            <>
              {" "}
              On pace for{" "}
              <span className="font-semibold text-green">
                {new Date(eta.eta_date).toLocaleDateString("en-GB", {
                  month: "long",
                  year: "numeric",
                })}
              </span>
              .
            </>
          ) : null}
        </Lead>
      </div>

      <Card>
        <div className="flex gap-1.5">
          {CEFR_LEVELS.map((label, i) => {
            const fill = i < currentIdx ? 100 : i === currentIdx ? Math.max(withinPct, 6) : 0;
            return (
              <div key={label} className="flex-1">
                <div className="h-3 overflow-hidden rounded-md bg-track">
                  <div
                    className={`h-full ${i < currentIdx ? "bg-green" : "bg-accent"}`}
                    style={{ width: `${fill}%` }}
                  />
                </div>
                <div className="mt-1.5 flex justify-between">
                  <span
                    className={`font-mono text-[11px] font-semibold ${
                      i < currentIdx
                        ? "text-green"
                        : i === currentIdx
                          ? "text-accent"
                          : "text-ink-faint"
                    }`}
                  >
                    {label}
                  </span>
                  <span className="text-[10.5px] text-ink-faint">
                    {i < currentIdx ? "done" : i === currentIdx ? `you · ${withinPct}%` : ""}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      <div className="grid gap-3.5 md:grid-cols-2">
        <Card testid="skill-balance">
          <CardLabel>Skill balance</CardLabel>
          <div className="mt-4 grid gap-3">
            {data.skills.map((s) => {
              const pct = Math.round(Math.min(1, Math.max(0, s.pct)) * 100);
              return (
                <div key={s.skill} className="flex items-center gap-3" data-testid={`skill-${s.skill}`}>
                  <span className="w-[76px] flex-none text-[13px] font-semibold">
                    {SKILL_LABELS[s.skill] ?? s.skill}
                  </span>
                  <div className="h-[7px] flex-1 overflow-hidden rounded-[4px] bg-track">
                    <div
                      className={`h-full ${pct < 40 ? "bg-gold-text" : "bg-green"}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="w-[30px] flex-none text-right font-mono text-[10.5px] text-ink-soft">
                    {s.cefr}
                  </span>
                </div>
              );
            })}
          </div>
          <p className="mt-4 text-[12.5px] text-ink-soft">
            The daily session leans toward whichever bar lags — no extra planning needed.
          </p>
        </Card>

        <Card testid="cando-checklist">
          <CardLabel>Can-do statements</CardLabel>
          <ul className="mt-4 grid gap-2.5">
            {data.cando.items.map((cd) => (
              <li key={cd.id} data-testid="cando-item" className="flex items-baseline gap-2.5">
                <span
                  aria-hidden
                  className={`w-3.5 flex-none text-xs font-bold ${
                    cd.status === "confirmed" ? "text-green" : "text-ink-faint"
                  }`}
                >
                  {cd.status === "confirmed" ? "✓" : "○"}
                </span>
                <span
                  className={`text-[13.5px] leading-normal ${
                    cd.status === "confirmed" ? "" : "text-ink-soft"
                  }`}
                >
                  {cd.text}
                  <span className="ml-2 font-mono text-[9px] tracking-[0.1em] text-ink-faint uppercase">
                    {cd.cefr} · {cd.skill}
                  </span>
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-4 text-[12.5px] text-ink-soft" data-testid="cando-count">
            {data.cando.confirmed} of {data.cando.total} confirmed in live speaking checks
          </p>
        </Card>
      </div>

      <div className="grid gap-3.5 md:grid-cols-[1.4fr_1fr]">
        <div className="rounded-card bg-bark px-[22px] py-5 text-paper">
          <p className="text-[11px] font-bold tracking-[0.13em] text-bark-mist uppercase">
            Hear yourself change
          </p>
          <p className="mt-3 text-[13px] leading-relaxed text-bark-mute">
            Every speaking take is kept. Record one this week, another next month — same phrase,
            weeks apart. This is why you keep the recordings.
          </p>
        </div>
        <Card className="flex flex-col justify-center gap-3">
          <div className="flex items-baseline justify-between" data-testid="total-time">
            <span className="text-[13px] text-ink-soft">Total time</span>
            <span className="font-mono text-[15px] font-semibold">{data.totals.hours_total} h</span>
          </div>
          <div className="flex items-baseline justify-between" data-testid="weekly-average">
            <span className="text-[13px] text-ink-soft">Weekly average</span>
            <span className="font-mono text-[15px] font-semibold">
              {data.totals.weekly_avg_hours} h
            </span>
          </div>
          <div className="flex items-baseline justify-between" data-testid="sentences-spoken">
            <span className="text-[13px] text-ink-soft">Sentences spoken</span>
            <span className="font-mono text-[15px] font-semibold">
              {data.totals.sentences_spoken}
            </span>
          </div>
        </Card>
      </div>

      <section
        data-testid="consistency-progress"
        className="rounded-card border border-amber-line bg-amber-soft px-5 py-4"
      >
        <p className="text-[11px] font-bold tracking-[0.13em] text-amber-text uppercase">
          Consistency
        </p>
        <p className="ky mt-1.5 text-lg">
          {consistencyLabel(data.consistency.active_days, data.consistency.window_days)}
        </p>
        <p className="mt-1 text-[13px] text-amber-deep">
          Rhythm beats streaks — one rest day never resets you.
        </p>
      </section>
    </div>
  );
}
