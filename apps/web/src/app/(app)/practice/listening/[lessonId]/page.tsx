"use client";

import { use, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getRoadmap, lessonFromRoadmap } from "@/lib/api/endpoints";
import { prefetchAudio } from "@/lib/audio-prefetch";
import { AudioButton } from "@/components/AudioButton";
import { Mcq } from "@/components/Mcq";
import { Respelled } from "@/components/PronunciationGuide";
import { NORMAL_RATE, SLOW_RATE, SLOW_RATE_LABEL } from "@/lib/audio/rate";
import { useSlowAudio } from "@/lib/audio/rate-store";
import { Card, CardLabel, ErrorNote, Kicker, Lead, LoadingNote, PageTitle } from "@/components/ui";

const SPEAKERS = ["Emmanuel", "Diane"] as const;
const SPEAKER_COLORS = ["text-accent", "text-green"] as const;

export default function ListeningPage({
  params,
}: {
  params: Promise<{ lessonId: string }>;
}) {
  const { lessonId } = use(params);
  // Shares the ["roadmap"] cache with the sidebar/lesson screens — the
  // listening lines are the lesson's items out of the same payload.
  const roadmapQuery = useQuery({ queryKey: ["roadmap"], queryFn: getRoadmap });
  const view = useMemo(
    () => (roadmapQuery.data ? lessonFromRoadmap(roadmapQuery.data, lessonId) : null),
    [roadmapQuery.data, lessonId],
  );
  const items = useMemo(() => view?.lesson.items ?? [], [view]);
  const [played, setPlayed] = useState(false);
  const [transcriptOpen, setTranscriptOpen] = useState(false);
  // This screen owns its speed: the segmented control is an explicit choice
  // for this listen. Until it is touched it follows the app-wide preference,
  // so "always slowly" lands on the learner speed without contradicting the
  // label sitting right under the player.
  const alwaysSlow = useSlowAudio();
  const [chosenSpeed, setChosenSpeed] = useState<0 | 1 | null>(null);
  const speed: 0 | 1 = chosenSpeed ?? (alwaysSlow ? 0 : 1);

  // Warm the lesson's lines so the first play is instant.
  useEffect(() => {
    prefetchAudio(items.map((i) => i.audio_url));
  }, [items]);

  if (roadmapQuery.isPending) return <LoadingNote label="Cueing the voices…" />;
  if (roadmapQuery.isError || !view) {
    return <ErrorNote message="This listening exercise couldn't load." />;
  }

  const { lesson } = view;

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
                src={item.audio_url}
                tone="gold"
                rate={speed === 0 ? SLOW_RATE : NORMAL_RATE}
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
          {([`${SLOW_RATE_LABEL} learner`, "1× street"] as const).map((label, i) => (
            <button
              key={label}
              type="button"
              data-testid="listening-speed"
              onClick={() => setChosenSpeed(i as 0 | 1)}
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
                  <Respelled
                    text={item.sentence}
                    guide={item.pronunciation}
                    className="ky text-[16.5px]"
                  />
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
