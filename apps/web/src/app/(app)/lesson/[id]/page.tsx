"use client";

import Link from "next/link";
import { use, useEffect, useMemo } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { getRoadmap, lessonFromRoadmap, postAttempt } from "@/lib/api/endpoints";
import { prefetchAudio } from "@/lib/audio-prefetch";
import { lessonQuiz } from "@/lib/quiz";
import { AudioButton } from "@/components/AudioButton";
import { Markdown } from "@/components/Markdown";
import { Quiz } from "@/components/Quiz";
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
  const view = useMemo(
    () => (roadmapQuery.data ? lessonFromRoadmap(roadmapQuery.data, id) : null),
    [roadmapQuery.data, id],
  );
  const items = useMemo(() => view?.lesson.items ?? [], [view]);

  // Quick-check answers are recorded as read-mode attempts so the item feeds SRS.
  const attempt = useMutation({ mutationFn: postAttempt });

  // Warm this lesson's audio as soon as it opens so the first tap is instant.
  useEffect(() => {
    prefetchAudio(items.map((i) => i.audio_url));
  }, [items]);

  if (roadmapQuery.isPending) return <LoadingNote label="Opening the lesson…" />;
  if (roadmapQuery.isError || !view) {
    return <ErrorNote message="This lesson couldn't load. Head back to the roadmap and try again." />;
  }

  const { lesson, unitTitle, levelCefr, lessonNumber, lessonCount } = view;
  const situationTag = items[0]?.tags?.[0];
  // quiz[] when the payload has it; the legacy single quick_check otherwise.
  const quizQuestions = lessonQuiz(lesson);

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
                <AudioButton itemId={item.id} src={item.audio_url} label={`Play “${item.sentence}”`} />
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

      {quizQuestions.length > 0 ? (
        <Card testid="quick-check">
          <CardLabel>Lesson check</CardLabel>
          <div className="mt-1.5">
            <Quiz
              key={lesson.id}
              questions={quizQuestions}
              onAnswered={(question, correct) => {
                // One read-mode attempt per question so each item feeds SRS.
                const itemId = question.item_id ?? items[0]?.id;
                if (itemId) {
                  attempt.mutate({ item_id: itemId, mode: "read", score: correct ? 1 : 0 });
                }
              }}
            />
          </div>
        </Card>
      ) : null}

      {view.prev || view.next ? (
        <nav
          className="mt-1.5 flex items-center justify-between gap-3"
          aria-label="Lesson navigation"
          data-testid="lesson-nav"
        >
          {view.prev ? (
            <Link
              href={`/lesson/${view.prev.id}`}
              className={btnGhost}
              data-testid="lesson-prev"
              title={view.prev.title}
            >
              ← Lesson {view.prev.label}
            </Link>
          ) : (
            <span aria-hidden />
          )}
          {view.next ? (
            view.next.status !== "locked" ? (
              <Link
                href={`/lesson/${view.next.id}`}
                className={btnGhost}
                data-testid="lesson-next"
                data-status={view.next.status}
                title={view.next.title}
              >
                Lesson {view.next.label} →
              </Link>
            ) : (
              <span
                className={`${btnGhost} cursor-default opacity-50 hover:border-line-strong hover:text-ink-soft`}
                aria-disabled="true"
                data-testid="lesson-next"
                data-status="locked"
                title="Finish the road to here first"
              >
                Lesson {view.next.label} · Locked
              </span>
            )
          ) : null}
        </nav>
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-3">
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
