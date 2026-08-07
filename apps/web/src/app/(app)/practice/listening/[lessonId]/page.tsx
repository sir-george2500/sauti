"use client";

import { use, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getLesson } from "@/lib/api/endpoints";
import { AudioButton } from "@/components/AudioButton";
import { Mcq } from "@/components/Mcq";
import { Card, ErrorNote, Kicker, LoadingNote, PageTitle } from "@/components/ui";

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
  const [transcriptOpen, setTranscriptOpen] = useState(false);

  if (lessonQuery.isPending) return <LoadingNote label="Cueing the voices…" />;
  if (lessonQuery.isError || !lessonQuery.data) {
    return <ErrorNote message="This listening exercise couldn't load." />;
  }

  const { lesson } = lessonQuery.data;
  const items = lesson.items ?? [];

  return (
    <div className="grid gap-6">
      <div>
        <Kicker>Practice · Listening</Kicker>
        <PageTitle>{lesson.title}</PageTitle>
        <p className="mt-2 max-w-lg text-ink-soft">
          Native voices, real speed. Listen once before opening the transcript.
        </p>
      </div>

      <Card testid="listening-player">
        <div className="grid gap-3">
          {items.map((item, i) => (
            <div
              key={item.id}
              className="flex items-center gap-4 rounded-xl border border-line bg-paper px-4 py-3"
              onClickCapture={() => setPlayed(true)}
            >
              <AudioButton itemId={item.id} testid="listening-play" />
              <span className="text-sm text-ink-soft">Line {i + 1}</span>
            </div>
          ))}
        </div>
        <p className="mt-4 text-[10px] font-semibold tracking-[0.16em] text-ink-soft uppercase">
          <span className="text-accent">●</span> Emmanuel &amp; Diane · Kigali
        </p>
      </Card>

      {lesson.quick_check ? (
        <Card testid="comprehension">
          <h2 className="ky text-xl font-semibold">Comprehension</h2>
          <div className="mt-4">
            <Mcq quickCheck={lesson.quick_check} optionTestid="comprehension-option" />
          </div>
        </Card>
      ) : null}

      <Card testid="transcript-card">
        <div className="flex items-center justify-between gap-3">
          <h2 className="ky text-xl font-semibold">Transcript</h2>
          <button
            type="button"
            data-testid="transcript-toggle"
            disabled={!played && !transcriptOpen}
            onClick={() => setTranscriptOpen((v) => !v)}
            className="rounded-full border border-line bg-cream px-4 py-1.5 text-sm transition-colors hover:border-accent disabled:opacity-50"
          >
            {transcriptOpen ? "Hide" : played ? "Reveal" : "Listen once first"}
          </button>
        </div>
        {transcriptOpen ? (
          <ul className="mt-4 grid gap-3" data-testid="transcript">
            {items.map((item, i) => (
              <li key={item.id} className="border-l-2 border-line pl-4">
                <p className="text-[10px] font-semibold tracking-[0.14em] text-ink-soft uppercase">
                  {i % 2 === 0 ? "Emmanuel" : "Diane"}
                </p>
                <p className="ky text-lg">{item.sentence}</p>
                <p className="text-sm text-ink-soft">{item.gloss}</p>
              </li>
            ))}
          </ul>
        ) : null}
      </Card>
    </div>
  );
}
