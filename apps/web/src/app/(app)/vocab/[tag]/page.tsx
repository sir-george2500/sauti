"use client";

import Link from "next/link";
import { use, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getVocabDeck, postAttempt } from "@/lib/api/endpoints";
import { reviewAttemptPayload } from "@/lib/srs";
import { AudioButton } from "@/components/AudioButton";
import { btnGhost, btnPrimary, Card, ErrorNote, Kicker, Lead, LoadingNote, PageTitle } from "@/components/ui";
import type { SrsGradeLabel } from "@/lib/api/types";

const GRADES: { label: SrsGradeLabel; text: string; sub: string }[] = [
  { label: "again", text: "Again", sub: "blank" },
  { label: "hard", text: "Hard", sub: "strained" },
  { label: "good", text: "Good", sub: "came back" },
  { label: "easy", text: "Easy", sub: "instant" },
];

export default function DeckReviewPage({ params }: { params: Promise<{ tag: string }> }) {
  const { tag } = use(params);
  const queryClient = useQueryClient();
  const deckQuery = useQuery({
    queryKey: ["vocab-deck", tag],
    queryFn: () => getVocabDeck(tag),
  });

  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [reviewed, setReviewed] = useState(0);

  const attempt = useMutation({
    mutationFn: postAttempt,
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ["vocab-decks"] });
    },
  });

  if (deckQuery.isPending) return <LoadingNote label="Shuffling the deck…" />;
  if (deckQuery.isError) return <ErrorNote message="This deck couldn't load." />;

  const deck = deckQuery.data;
  const items = deck.items;
  const current = items[index];
  const done = !current;

  const grade = (label: SrsGradeLabel) => {
    if (!current) return;
    attempt.mutate(reviewAttemptPayload(current.id, label));
    setReviewed((n) => n + 1);
    setRevealed(false);
    setIndex((i) => i + 1);
  };

  return (
    <div className="grid gap-3.5">
      <div className="mb-2">
        <Kicker>Vocabulary · {deck.title}</Kicker>
        <PageTitle>{done ? "Deck rested." : deck.title}</PageTitle>
        <Lead>
          {done
            ? `${reviewed} sentence${reviewed === 1 ? "" : "s"} reviewed — spacing does the remembering now.`
            : `Card ${index + 1} of ${items.length} — say it out loud before you flip.`}
        </Lead>
      </div>

      {done ? (
        <Card testid="review-done" className="text-center">
          <p className="ky text-2xl font-semibold">Byiza cyane!</p>
          <p className="mt-2 text-sm text-ink-soft">
            Everything due here is rescheduled. Come back when the rhythm calls.
          </p>
          <Link href="/vocab" data-testid="back-to-decks" className={`mt-5 ${btnPrimary}`}>
            Back to decks
          </Link>
        </Card>
      ) : (
        <Card testid="review-card">
          <div className="flex min-h-[220px] flex-col items-center justify-center gap-4 py-6 text-center">
            <div className="flex items-center gap-3.5">
              <AudioButton itemId={current.id} />
              <p className="ky text-[26px] leading-snug font-semibold sm:text-[30px]">
                {current.sentence}
              </p>
            </div>
            {revealed ? (
              <p className="text-lg text-ink-soft" data-testid="review-gloss">
                {current.gloss}
              </p>
            ) : (
              <button
                type="button"
                data-testid="reveal-card"
                onClick={() => setRevealed(true)}
                className={btnGhost}
              >
                Show meaning
              </button>
            )}
          </div>

          {revealed ? (
            <div className="grid grid-cols-2 gap-2 border-t border-line pt-4 sm:grid-cols-4">
              {GRADES.map((g) => (
                <button
                  key={g.label}
                  type="button"
                  data-testid={`grade-${g.label}`}
                  onClick={() => grade(g.label)}
                  className={`cursor-pointer rounded-btn border-[1.5px] px-3 py-2.5 text-center transition-colors ${
                    g.label === "good" || g.label === "easy"
                      ? "border-line bg-card hover:border-green hover:bg-green-soft"
                      : "border-line bg-card hover:border-accent hover:bg-accent-soft"
                  }`}
                >
                  <span className="block text-sm font-semibold">{g.text}</span>
                  <span className="block text-xs text-ink-soft">{g.sub}</span>
                </button>
              ))}
            </div>
          ) : null}
        </Card>
      )}
    </div>
  );
}
