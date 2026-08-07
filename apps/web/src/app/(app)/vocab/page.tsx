"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { getVocabDecks } from "@/lib/api/endpoints";
import { btnGreen, ErrorNote, Kicker, Lead, LoadingNote, PageTitle } from "@/components/ui";

export default function VocabPage() {
  const decks = useQuery({ queryKey: ["vocab-decks"], queryFn: getVocabDecks });

  const firstDue = decks.data?.decks.find((d) => d.due_count > 0);
  const totalDue = decks.data?.total_due ?? 0;

  return (
    <div className="grid gap-3.5">
      <div className="mb-2 flex flex-wrap items-end justify-between gap-5">
        <div>
          <Kicker>Learn · Vocabulary</Kicker>
          <PageTitle>Words where you&rsquo;ll use them.</PageTitle>
          <Lead className="max-w-lg">
            Organized by situation, not alphabet — every word arrives inside a sentence
            you&rsquo;d actually say.
          </Lead>
        </div>
        {firstDue ? (
          <Link
            href={`/vocab/${encodeURIComponent(firstDue.tag)}`}
            data-testid="review-due"
            className={btnGreen}
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
        <div className="grid gap-3.5 sm:grid-cols-2">
          {decks.data.decks.map((deck) => {
            const pct = Math.round(deck.mastery * 100);
            return (
              <Link
                key={deck.tag}
                href={`/vocab/${encodeURIComponent(deck.tag)}`}
                data-testid="vocab-deck"
                className="rounded-card border border-line bg-card p-5 shadow-card transition-colors hover:border-accent"
              >
                <div className="flex items-baseline justify-between gap-3">
                  <p className="ky text-[19px] font-semibold">{deck.title}</p>
                  <span
                    className={`font-mono text-[11px] ${pct > 0 ? "text-accent" : "text-ink-faint"}`}
                  >
                    {pct}%
                  </span>
                </div>
                <p className="mt-0.5 mb-3.5 text-[13px] text-ink-soft">
                  {deck.gloss} · {deck.word_count} words
                </p>
                <div className="mb-3 h-1.5 overflow-hidden rounded-[3px] bg-track">
                  <div
                    className={`h-full ${pct >= 80 ? "bg-green" : "bg-accent"}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                {deck.sample ? (
                  <p className="text-[13px] text-ink-soft">
                    <span className="ky text-ink italic">{deck.sample.sentence}</span> —{" "}
                    {deck.sample.gloss}
                  </p>
                ) : null}
                {deck.due_count > 0 ? (
                  <p className="mt-3 text-xs font-semibold text-accent" data-testid="deck-due">
                    {deck.due_count} due for review
                  </p>
                ) : (
                  <p className="mt-3 text-xs text-ink-faint">All rested — nothing due.</p>
                )}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
