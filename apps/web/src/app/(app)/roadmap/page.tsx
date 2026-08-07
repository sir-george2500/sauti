"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { getRoadmap } from "@/lib/api/endpoints";
import { Card, ErrorNote, Kicker, LoadingNote, PageTitle } from "@/components/ui";
import type { RoadmapStatus } from "@/lib/api/types";

const LEVEL_DESCRIPTIONS: Record<string, string> = {
  A1: "First greetings, family, getting around.",
  A2: "Market, money, daily errands — real transactions.",
  B1: "Conversational: opinions, plans, stories.",
  B2: "Work and argument — fluent in most rooms.",
  C1: "Nuance, humour, radio-speed listening.",
  C2: "Full fluency — proverbs land, jokes too.",
};

function statusMark(status: RoadmapStatus): string {
  switch (status) {
    case "done":
      return "✓";
    case "current":
      return "●";
    default:
      return "";
  }
}

export default function RoadmapPage() {
  const roadmap = useQuery({ queryKey: ["roadmap"], queryFn: getRoadmap });

  return (
    <div className="grid gap-6">
      <div>
        <Kicker>Ikinyarwanda · Roadmap</Kicker>
        <PageTitle>From first greeting to full fluency.</PageTitle>
        <p className="mt-2 max-w-lg text-ink-soft">
          Six CEFR stages, each closed by a real speaking check. Not sure where you stand?{" "}
          <Link
            href="/placement"
            className="text-accent-deep underline underline-offset-2"
            data-testid="placement-cta"
          >
            Take the placement.
          </Link>
        </p>
      </div>

      {roadmap.isPending ? (
        <LoadingNote label="Drawing the road…" />
      ) : roadmap.isError ? (
        <ErrorNote message="The roadmap couldn't load. Refresh to try again." />
      ) : (
        <ol className="grid gap-4" data-testid="roadmap-levels">
          {roadmap.data.levels.map((level) => {
            const open = level.status === "current" || level.status === "done";
            return (
              <li key={level.cefr}>
                <Card
                  testid={`roadmap-level-${level.cefr}`}
                  className={level.status === "locked" ? "opacity-70" : ""}
                >
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <div className="flex items-baseline gap-3">
                      <span
                        className={`ky text-2xl font-semibold ${
                          level.status === "current" ? "text-accent-deep" : ""
                        }`}
                      >
                        {level.cefr}
                      </span>
                      <span className="ky text-lg">{level.title}</span>
                    </div>
                    <span className="text-[10px] font-semibold tracking-[0.16em] text-ink-soft uppercase">
                      {level.status === "done"
                        ? "Completed"
                        : level.status === "current"
                          ? "You are here"
                          : "Speaking check to open"}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-ink-soft">
                    {LEVEL_DESCRIPTIONS[level.cefr] ?? ""}
                  </p>
                  {open && level.units.length > 0 ? (
                    <ul className="mt-4 grid gap-2 sm:grid-cols-2">
                      {level.units.map((unit) => {
                        const firstLesson =
                          unit.lessons.find((l) => l.status === "current") ??
                          unit.lessons.find((l) => l.status !== "done") ??
                          unit.lessons[0];
                        const inner = (
                          <span className="flex items-center justify-between gap-2">
                            <span>
                              <span className="mr-2 text-xs text-ink-soft">U{unit.ord}</span>
                              {unit.title}
                            </span>
                            <span className="text-accent-deep">{statusMark(unit.status)}</span>
                          </span>
                        );
                        return (
                          <li key={unit.id}>
                            {firstLesson && unit.status !== "locked" ? (
                              <Link
                                href={`/lesson/${firstLesson.id}`}
                                data-testid="roadmap-unit"
                                className={`block rounded-xl border px-4 py-3 text-sm transition-colors ${
                                  unit.status === "current"
                                    ? "border-accent bg-accent-soft"
                                    : "border-line bg-paper hover:border-accent"
                                }`}
                              >
                                {inner}
                              </Link>
                            ) : (
                              <span
                                data-testid="roadmap-unit"
                                className="block rounded-xl border border-line bg-paper px-4 py-3 text-sm opacity-70"
                              >
                                {inner}
                              </span>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  ) : null}
                </Card>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}
