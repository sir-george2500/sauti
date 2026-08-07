"use client";

import Link from "next/link";
import { use } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { getRoadmap, lessonFromRoadmap, postAttempt } from "@/lib/api/endpoints";
import { AudioButton } from "@/components/AudioButton";
import { Markdown } from "@/components/Markdown";
import { Mcq } from "@/components/Mcq";
import {
  btnGhost,
  btnPrimary,
  Card,
  CardLabel,
  ErrorNote,
  Kicker,
  LoadingNote,
  PageTitle,
} from "@/components/ui";

const VOICES = ["Diane", "Emmanuel"] as const;

export default function LessonPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  // Lesson content lives inside the roadmap payload; sharing the ["roadmap"]
  // key with the sidebar and other screens means one fetch serves all of them.
  const roadmapQuery = useQuery({ queryKey: ["roadmap"], queryFn: getRoadmap });
  const view = roadmapQuery.data ? lessonFromRoadmap(roadmapQuery.data, id) : null;

  // Quick-check answers are recorded as read-mode attempts so the item feeds SRS.
  const attempt = useMutation({ mutationFn: postAttempt });

  if (roadmapQuery.isPending) return <LoadingNote label="Opening the lesson…" />;
  if (roadmapQuery.isError || !view) {
    return <ErrorNote message="This lesson couldn't load. Head back to the roadmap and try again." />;
  }

  const { lesson, unitTitle, levelCefr, lessonNumber, lessonCount } = view;
  const items = lesson.items ?? [];
  const situationTag = items[0]?.tags?.[0];

  return (
    <article className="grid gap-3.5" data-testid="lesson">
      <div className="mb-2">
        <Kicker>
          {levelCefr} · {unitTitle} · Lesson {lessonNumber} of {lessonCount}
        </Kicker>
        <PageTitle>{lesson.title}</PageTitle>
      </div>

      {lesson.grammar_md ? (
        <Card>
          <Markdown source={lesson.grammar_md} />
        </Card>
      ) : null}

      {items.length > 0 ? (
        <Card testid="hear-it-used">
          <CardLabel>Hear it used</CardLabel>
          <ul className="mt-4 grid gap-4">
            {items.map((item, i) => (
              <li key={item.id} className="flex items-center gap-3.5" data-testid="example-row">
                <AudioButton itemId={item.id} label={`Play “${item.sentence}”`} />
                <div className="min-w-0 flex-1">
                  <p className="ky text-lg">{item.sentence}</p>
                  <p className="mt-0.5 text-[12.5px] text-ink-soft">{item.gloss}</p>
                </div>
                <span className="flex-none font-mono text-[10px] text-ink-faint uppercase">
                  {VOICES[i % VOICES.length]}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {lesson.culture_note ? (
        <section
          data-testid="umuco-note"
          className="rounded-card border border-amber-line bg-amber-soft px-5 py-[18px] sm:px-[22px]"
        >
          <p className="text-[10.5px] font-bold tracking-[0.13em] text-amber-text uppercase">
            Umuco · Culture
          </p>
          <p className="mt-1.5 text-sm leading-[1.6] text-amber-deep">{lesson.culture_note}</p>
        </section>
      ) : null}

      {lesson.quick_check ? (
        <Card testid="quick-check">
          <CardLabel>Quick check</CardLabel>
          <div className="mt-1.5">
            <Mcq
              quickCheck={lesson.quick_check}
              onAnswered={(correct) => {
                const firstItem = items[0];
                if (firstItem) {
                  attempt.mutate({
                    item_id: firstItem.id,
                    mode: "read",
                    score: correct ? 1 : 0,
                  });
                }
              }}
            />
          </div>
        </Card>
      ) : null}

      <div className="mt-1.5 flex flex-wrap items-center justify-between gap-3">
        <Link href="/roadmap" className={btnGhost} data-testid="back-to-roadmap">
          ← Back to roadmap
        </Link>
        <Link
          href={situationTag ? `/vocab/${encodeURIComponent(situationTag)}` : "/vocab"}
          data-testid="practice-words"
          className={btnPrimary}
        >
          Practice these words →
        </Link>
      </div>
    </article>
  );
}
