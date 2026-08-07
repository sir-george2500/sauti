"use client";

import { useState } from "react";
import type { QuickCheck } from "@/lib/api/types";

/**
 * One-question multiple choice with feedback — used by the lesson quick
 * check and the listening comprehension question. Option treatment follows
 * the mockup: answered → correct turns green, a wrong pick turns terracotta.
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
      <div className="mt-3.5 grid gap-2">
        {quickCheck.options.map((o, i) => {
          let cls = "border-line bg-card hover:border-accent";
          let mark: string | null = null;
          let markCls = "";
          if (answered && o.correct) {
            cls = "border-green bg-green-soft";
            mark = "✓";
            markCls = "text-green";
          } else if (answered && i === picked) {
            cls = "border-ember bg-accent-soft";
            mark = "×";
            markCls = "text-accent";
          } else if (answered) {
            cls = "border-line bg-card";
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
              className={`flex cursor-pointer items-center gap-2.5 rounded-btn border-[1.5px] px-4 py-3 text-left transition-colors disabled:cursor-default ${cls}`}
            >
              <span className="ky flex-1 text-base">{o.text}</span>
              {mark ? (
                <span className={`text-[13px] font-bold ${markCls}`} aria-hidden>
                  {mark}
                </span>
              ) : null}
            </button>
          );
        })}
      </div>
      {answered ? (
        <p
          className={`mt-3 text-[13.5px] font-semibold ${correct ? "text-green" : "text-accent"}`}
          data-testid="mcq-feedback"
        >
          {correct
            ? "Yego! That's the one — the prefix does the work."
            : `Not quite — the natural choice is “${quickCheck.options.find((o) => o.correct)?.text ?? ""}”. Rest easy, it comes back in review.`}
        </p>
      ) : null}
    </div>
  );
}
