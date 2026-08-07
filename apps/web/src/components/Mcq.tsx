"use client";

import { useState } from "react";
import type { QuickCheck } from "@/lib/api/types";

/**
 * One-question multiple choice with feedback — used by the lesson quick
 * check and the listening comprehension question.
 */
export function Mcq({
  quickCheck,
  optionTestid = "quick-check-option",
  onAnswered,
}: {
  quickCheck: QuickCheck;
  optionTestid?: string;
  onAnswered?: (correct: boolean) => void;
}) {
  const [picked, setPicked] = useState<number | null>(null);
  const answered = picked !== null;
  const correct = answered && quickCheck.options[picked]?.correct === true;

  return (
    <div>
      <p className="ky text-lg">{quickCheck.question}</p>
      <div className="mt-4 grid gap-2">
        {quickCheck.options.map((o, i) => {
          let cls = "border-line bg-card hover:border-accent";
          if (answered && i === picked) {
            cls = o.correct
              ? "border-accent bg-accent-soft"
              : "border-accent/40 bg-cream opacity-80";
          } else if (answered && o.correct) {
            cls = "border-accent bg-accent-soft";
          } else if (answered) {
            cls = "border-line bg-card opacity-60";
          }
          return (
            <button
              key={i}
              type="button"
              data-testid={optionTestid}
              disabled={answered}
              onClick={() => {
                setPicked(i);
                onAnswered?.(o.correct);
              }}
              className={`flex items-center justify-between rounded-xl border px-4 py-3 text-left transition-colors ${cls}`}
            >
              <span className="ky">{o.text}</span>
              {answered && (i === picked || o.correct) ? (
                <span className="text-sm" aria-hidden>
                  {o.correct ? "✓" : "✕"}
                </span>
              ) : null}
            </button>
          );
        })}
      </div>
      {answered ? (
        <p className="mt-3 text-sm text-ink-soft" data-testid="mcq-feedback">
          {correct
            ? "Yego! That's the one — the prefix does the work."
            : `Not quite — the natural choice is “${quickCheck.options.find((o) => o.correct)?.text ?? ""}”. Rest easy, it comes back in review.`}
        </p>
      ) : null}
    </div>
  );
}
