"use client";

import { use, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getLesson } from "@/lib/api/endpoints";
import { AudioButton } from "@/components/AudioButton";
import { Mcq } from "@/components/Mcq";
import { Card, CardLabel, ErrorNote, Kicker, Lead, LoadingNote, PageTitle } from "@/components/ui";

const SPEAKERS = ["Emmanuel", "Diane"] as const;
const SPEAKER_COLORS = ["text-accent", "text-green"] as const;

export default function ListeningPage({
  params,
}: {
  params: Promise<{ lessonId: string }>;
}) {
  const { lessonId } = use(params);
  const lessonQuery = useQuery({
    queryKey: ["lesson", lessonId],
    queryFn: () => getLesson(lessonId),
  });
  const [played, setPlayed] = useState(false);
  const [speed, setSpeed] = useState<0 | 1>(1);
  const [transcriptOpen, setTranscriptOpen] = useState(false);

  if (lessonQuery.isPending) return <LoadingNote label="Cueing the voices…" />;
  if (lessonQuery.isError || !lessonQuery.data) {
    return <ErrorNote message="This listening exercise couldn't load." />;
  }

  const { lesson } = lessonQuery.data;
  const items = lesson.items ?? [];

  return (
    <div className="grid gap-3.5">
      <div className="mb-2">
        <Kicker>Practice · Listening</Kicker>
        <PageTitle>{lesson.title}</PageTitle>
        <Lead>Native voices, real speed. Listen once before opening the transcript.</Lead>
      </div>

      <div
        className="rounded-card bg-bark p-6 text-paper"
        data-testid="listening-player"
        onClickCapture={() => setPlayed(true)}
      >
        <div className="grid gap-3">
          {items.map((item, i) => (
            <div key={item.id} className="flex items-center gap-4">
              <AudioButton
                itemId={item.id}
                tone="gold"
                slow={speed === 0}
                testid="listening-play"
                label={`Play line ${i + 1}`}
              />
              <div className="flex h-8 flex-1 items-end gap-[2px]" aria-hidden>
                {Array.from({ length: 36 }, (_, b) => (
                  <span
                    key={b}
                    className="w-1 rounded-[2px] bg-bark-mist"
                    style={{ height: `${6 + ((b * 7 + i * 11) % 26)}px` }}
                  />
                ))}
              </div>
              <span className="flex-none font-mono text-[11px] text-bark-mute">
                Line {i + 1}
              </span>
            </div>
          ))}
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          {(["0.7× learner", "1× street"] as const).map((label, i) => (
            <button
              key={label}
              type="button"
              onClick={() => setSpeed(i as 0 | 1)}
              aria-pressed={speed === i}
              className={`cursor-pointer rounded-full px-3.5 py-[7px] text-xs font-semibold transition-colors ${
                speed === i
                  ? "border border-gold bg-gold text-bark"
                  : "border border-bark-line bg-transparent text-bark-mute hover:text-bark-glow"
              }`}
            >
              {label}
            </button>
          ))}
          <span className="ml-auto font-mono text-[10.5px] text-gold uppercase">
            ● Emmanuel &amp; Diane · Kigali
          </span>
        </div>
      </div>

      {lesson.quick_check ? (
        <Card testid="comprehension">
          <CardLabel>Comprehension</CardLabel>
          <div className="mt-1.5">
            <Mcq quickCheck={lesson.quick_check} optionTestid="comprehension-option" />
          </div>
        </Card>
      ) : null}

      <Card testid="transcript-card">
        <div className="flex items-center justify-between gap-3">
          <CardLabel>Transcript</CardLabel>
          <button
            type="button"
            data-testid="transcript-toggle"
            disabled={!played && !transcriptOpen}
            onClick={() => setTranscriptOpen((v) => !v)}
            className="cursor-pointer rounded-lg border border-line-strong bg-transparent px-3.5 py-[7px] text-[12.5px] font-semibold text-ink-soft transition-colors hover:border-accent hover:text-accent disabled:cursor-default disabled:opacity-50"
          >
            {transcriptOpen ? "Hide" : played ? "Reveal" : "Listen once first"}
          </button>
        </div>
        {transcriptOpen ? (
          <ul className="mt-[18px] grid gap-3.5" data-testid="transcript">
            {items.map((item, i) => (
              <li key={item.id} className="flex items-baseline gap-3.5">
                <span
                  className={`w-[74px] flex-none font-mono text-[10.5px] uppercase ${SPEAKER_COLORS[i % 2]}`}
                >
                  {SPEAKERS[i % 2]}
                </span>
                <div>
                  <p className="ky text-[16.5px]">{item.sentence}</p>
                  <p className="mt-0.5 text-[12.5px] text-ink-soft">{item.gloss}</p>
                </div>
              </li>
            ))}
          </ul>
        ) : null}
      </Card>
    </div>
  );
}
