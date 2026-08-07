"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { getRoadmap } from "@/lib/api/endpoints";
import { Card, ErrorNote, Kicker, Lead, LoadingNote, PageTitle } from "@/components/ui";
import type { RoadmapLevel, RoadmapUnit } from "@/lib/api/types";

const LEVEL_DESCRIPTIONS: Record<string, string> = {
  A1: "Greetings, self-introduction, numbers, basic needs.",
  A2: "Daily life in short, real sentences — markets, family, getting around.",
  B1: "Tell stories, handle any daily situation, speak in past and future.",
  B2: "Debate, work meetings, nuance — comfortable at native speed.",
  C1: "Effortless conversation, humor, idiom — near-native range.",
  C2: "Full cultural and professional command.",
};

function levelBadgeClass(status: RoadmapLevel["status"]): string {
  if (status === "done") return "bg-green text-paper";
  if (status === "current") return "bg-accent text-on-accent";
  return "bg-track text-ink-soft";
}

function unitPct(unit: RoadmapUnit): number {
  if (unit.lessons.length === 0) return 0;
  return Math.round(
    (unit.lessons.filter((l) => l.status === "done").length / unit.lessons.length) * 100,
  );
}

function UnitRow({ unit }: { unit: RoadmapUnit }) {
  const firstLesson =
    unit.lessons.find((l) => l.status === "current") ??
    unit.lessons.find((l) => l.status !== "done") ??
    unit.lessons[0];

  const rowClass =
    unit.status === "current"
      ? "bg-accent-soft border border-accent-soft-line"
      : unit.status === "locked"
        ? "bg-[#FAF6EB] text-ink-soft"
        : "bg-[#FAF6EB]";
  const mark =
    unit.status === "done" ? (
      <span className="text-[13px] font-bold text-green">✓</span>
    ) : unit.status === "current" ? (
      <span className="text-xs font-bold text-accent">{unitPct(unit)}%</span>
    ) : null;

  const inner = (
    <>
      <span className="w-[22px] flex-none font-mono text-[11px] text-ink-soft">
        {String(unit.ord).padStart(2, "0")}
      </span>
      <span
        className={`flex-1 text-sm ${
          unit.status === "current"
            ? "font-semibold"
            : unit.status === "locked"
              ? "font-normal"
              : "font-medium"
        }`}
      >
        {unit.title}
      </span>
      {mark}
    </>
  );

  if (firstLesson && unit.status !== "locked") {
    return (
      <Link
        href={`/lesson/${firstLesson.id}`}
        data-testid="roadmap-unit"
        className={`mt-2.5 flex items-center gap-2.5 rounded-nav px-3 py-2.5 transition-colors hover:border-accent ${rowClass}`}
      >
        {inner}
      </Link>
    );
  }
  return (
    <span
      data-testid="roadmap-unit"
      className={`mt-2.5 flex items-center gap-2.5 rounded-nav px-3 py-2.5 ${rowClass}`}
    >
      {inner}
    </span>
  );
}

function LevelMeta({ level, eta }: { level: RoadmapLevel; eta?: string | null }) {
  if (level.status === "done") {
    return <span className="font-mono text-[11px] text-green uppercase">Complete</span>;
  }
  if (level.status === "current") {
    const currentUnit = level.units.find((u) => u.status === "current");
    return (
      <span className="font-mono text-[11px] text-accent">
        {currentUnit ? `Unit ${currentUnit.ord} of ${level.units.length} · ` : ""}You are here
      </span>
    );
  }
  if (eta) {
    return <span className="font-mono text-[11px] text-ink-soft uppercase">→ {eta}</span>;
  }
  return (
    <span className="font-mono text-[11px] text-ink-faint uppercase">Speaking check to open</span>
  );
}

export default function RoadmapPage() {
  const roadmap = useQuery({ queryKey: ["roadmap"], queryFn: getRoadmap });

  const eta = roadmap.data?.eta;
  const etaLabel = eta
    ? new Date(eta.eta_date).toLocaleDateString("en-US", { month: "long", year: "numeric" })
    : null;

  return (
    <div className="grid gap-3">
      <div className="mb-3">
        <Kicker>Ikinyarwanda · Roadmap</Kicker>
        <PageTitle>From first greeting to full fluency.</PageTitle>
        <Lead>
          Six CEFR stages, each closed by a real speaking check. Not sure where you stand?{" "}
          <Link
            href="/placement"
            className="font-semibold text-accent transition-colors hover:text-accent-deep"
            data-testid="placement-cta"
          >
            Take the placement.
          </Link>
        </Lead>
      </div>

      {roadmap.isPending ? (
        <LoadingNote label="Drawing the road…" />
      ) : roadmap.isError ? (
        <ErrorNote message="The roadmap couldn't load. Refresh to try again." />
      ) : (
        <ol className="grid gap-3" data-testid="roadmap-levels">
          {roadmap.data.levels.map((level) => (
            <li key={level.cefr}>
              <Card
                testid={`roadmap-level-${level.cefr}`}
                className={`px-5 py-5 sm:px-[22px] sm:py-5 ${
                  level.status === "current" ? "border-[#DDA073]" : ""
                }`}
              >
                <div className="flex items-center gap-3.5">
                  <span
                    className={`flex h-11 w-11 flex-none items-center justify-center rounded-btn font-mono text-[15px] font-semibold ${levelBadgeClass(level.status)}`}
                  >
                    {level.cefr}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="ky text-lg font-semibold">{level.title}</p>
                    <p className="mt-0.5 text-[13px] text-ink-soft">
                      {LEVEL_DESCRIPTIONS[level.cefr] ?? ""}
                    </p>
                  </div>
                  <LevelMeta
                    level={level}
                    eta={level.cefr === eta?.target_cefr ? etaLabel : null}
                  />
                </div>
                {level.status === "current" || level.status === "done" ? (
                  <div>
                    {level.units.map((unit) => (
                      <UnitRow key={unit.id} unit={unit} />
                    ))}
                  </div>
                ) : null}
              </Card>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
