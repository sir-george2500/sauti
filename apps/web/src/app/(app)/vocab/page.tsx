"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { getVocabDecks } from "@/lib/api/endpoints";
import { Card, ErrorNote, Kicker, LoadingNote, PageTitle } from "@/components/ui";

export default function VocabPage() {
  const decks = useQuery({ queryKey: ["vocab-decks"], queryFn: getVocabDecks });

  const firstDue = decks.data?.decks.find((d) => d.due_count > 0);
  const totalDue = decks.data?.total_due ?? 0;

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Kicker>Learn · Vocabulary</Kicker>
          <PageTitle>Words where you&rsquo;ll use them.</PageTitle>
          <p className="mt-2 max-w-lg text-ink-soft">
            Organized by situation, not alphabet — every word arrives inside a sentence
            you&rsquo;d actually say.
          </p>
        </div>
        {firstDue ? (
          <Link
            href={`/vocab/${encodeURIComponent(firstDue.tag)}`}
            data-testid="review-due"
            className="rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-paper transition-colors hover:bg-accent-deep"
          >
            Review {totalDue} due · {Math.max(2, Math.round(totalDue * 0.6))} min
          </Link>
        ) : null}
      </div>

      {decks.isPending ? (
        <LoadingNote label="Opening the decks…" />
      ) : decks.isError ? (
        <ErrorNote message="Your decks couldn't load. Refresh to try again." />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {decks.data.decks.map((deck) => (
            <Link key={deck.tag} href={`/vocab/${encodeURIComponent(deck.tag)}`}>
              <Card testid="vocab-deck" className="h-full transition-colors hover:border-accent">
                <div className="flex items-baseline justify-between gap-3">
                  <p className="ky text-xl font-semibold">{deck.title}</p>
                  <span className="text-sm font-medium text-accent-deep">
                    {Math.round(deck.mastery * 100)}%
                  </span>
                </div>
                <p className="mt-0.5 text-sm text-ink-soft">
                  {deck.gloss} · {deck.word_count} words
                </p>
                <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-cream">
                  <div
                    className="h-full rounded-full bg-accent"
                    style={{ width: `${Math.round(deck.mastery * 100)}%` }}
                  />
                </div>
                {deck.sample ? (
                  <p className="mt-3 text-sm">
                    <span className="ky">{deck.sample.sentence}</span>
                    <span className="text-ink-soft"> — {deck.sample.gloss}</span>
                  </p>
                ) : null}
                {deck.due_count > 0 ? (
                  <p className="mt-3 text-xs font-medium text-accent-deep" data-testid="deck-due">
                    {deck.due_count} due for review
                  </p>
                ) : (
                  <p className="mt-3 text-xs text-ink-soft">All rested — nothing due.</p>
                )}
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
