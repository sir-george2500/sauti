"use client";

import Link from "next/link";
import { use } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { getLesson, postAttempt } from "@/lib/api/endpoints";
import { AudioButton } from "@/components/AudioButton";
import { Markdown } from "@/components/Markdown";
import { Mcq } from "@/components/Mcq";
import { Card, ErrorNote, Kicker, LoadingNote, PageTitle, VoiceCredit } from "@/components/ui";

export default function LessonPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const lessonQuery = useQuery({
    queryKey: ["lesson", id],
    queryFn: () => getLesson(id),
  });

  // Quick-check answers are recorded as read-mode attempts so the item feeds SRS.
  const attempt = useMutation({ mutationFn: postAttempt });

  if (lessonQuery.isPending) return <LoadingNote label="Opening the lesson…" />;
  if (lessonQuery.isError || !lessonQuery.data) {
    return <ErrorNote message="This lesson couldn't load. Head back to the roadmap and try again." />;
  }

  const { lesson, unitTitle, levelCefr, lessonNumber, lessonCount } = lessonQuery.data;
  const items = lesson.items ?? [];
  const situationTag = items[0]?.tags?.[0];

  return (
    <article className="grid gap-6" data-testid="lesson">
      <div>
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
          <div className="flex items-center justify-between gap-3">
            <h2 className="ky text-xl font-semibold">Hear it used</h2>
            <VoiceCredit name="Diane" />
          </div>
          <ul className="mt-4 grid gap-3">
            {items.map((item) => (
              <li
                key={item.id}
                className="flex items-center gap-4 rounded-xl border border-line bg-paper px-4 py-3"
                data-testid="example-row"
              >
                <AudioButton itemId={item.id} label={`Play “${item.sentence}”`} />
                <div>
                  <p className="ky text-lg">{item.sentence}</p>
                  <p className="text-sm text-ink-soft">{item.gloss}</p>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {lesson.culture_note ? (
        <Card testid="umuco-note" className="border-accent/25 bg-accent-soft">
          <Kicker>Umuco · Culture</Kicker>
          <p className="mt-2 leading-relaxed">{lesson.culture_note}</p>
        </Card>
      ) : null}

      {lesson.quick_check ? (
        <Card testid="quick-check">
          <h2 className="ky text-xl font-semibold">Quick check</h2>
          <div className="mt-4">
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

      <div className="flex flex-wrap items-center justify-between gap-4">
        <Link
          href="/roadmap"
          className="text-sm text-ink-soft transition-colors hover:text-ink"
          data-testid="back-to-roadmap"
        >
          ← Back to roadmap
        </Link>
        <Link
          href={situationTag ? `/vocab/${encodeURIComponent(situationTag)}` : "/vocab"}
          data-testid="practice-words"
          className="rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-paper transition-colors hover:bg-accent-deep"
        >
          Practice these words →
        </Link>
      </div>
    </article>
  );
}
