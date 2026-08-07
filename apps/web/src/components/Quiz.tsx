"use client";

import { useReducer } from "react";
import type { QuizKind, QuizQuestion } from "@/lib/api/types";
import { initialQuizState, quizReducer, summarizeQuiz, type QuizAction, type QuizState } from "@/lib/quiz";
import { btnPrimary } from "@/components/ui";

const KIND_LABELS: Record<QuizKind, string> = {
  grammar: "Grammar",
  vocab: "Vocabulary",
  usage: "Usage",
  culture: "Culture",
};

/**
 * Multi-question lesson quiz — "question X of N", one answer per question
 * with immediate feedback + explanation, then a summary card with a per-kind
 * breakdown and a Retake. Replaces the single quick-check MCQ on the lesson
 * screen (the owner: "it should test every aspect").
 *
 * Option treatment matches Mcq: answered → the correct option turns green,
 * a wrong pick turns terracotta.
 */
export function Quiz({
  questions,
  onAnswered,
}: {
  questions: QuizQuestion[];
  /** Fires once per question, when it is answered. */
  onAnswered?: (question: QuizQuestion, correct: boolean) => void;
}) {
  const [state, dispatch] = useReducer(
    (s: QuizState, a: QuizAction) => quizReducer(questions, s, a),
    initialQuizState,
  );

  if (questions.length === 0) return null;

  if (state.finished) {
    const summary = summarizeQuiz(questions, state.answers);
    return (
      <div data-testid="quiz-summary" className="text-center">
        <p className="ky text-2xl font-semibold">
          You got {summary.correct} of {summary.total}
          {summary.correct === summary.total ? " — byiza cyane!" : " — retake?"}
        </p>
        <div className="mt-4 flex flex-wrap justify-center gap-2">
          {summary.byKind.map((k) => (
            <span
              key={k.kind}
              data-testid="quiz-kind-score"
              className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[12.5px] font-semibold ${
                k.correct === k.total
                  ? "border-green bg-green-soft text-green"
                  : "border-line-strong bg-card text-ink-soft"
              }`}
            >
              {KIND_LABELS[k.kind]} {k.correct}/{k.total}
            </span>
          ))}
        </div>
        <p className="mt-3 text-[13px] text-ink-soft">
          {summary.correct === summary.total
            ? "Every aspect holds — the review deck keeps it that way."
            : "Anything missed comes back in review — or run it again now."}
        </p>
        <button
          type="button"
          data-testid="quiz-retake"
          onClick={() => dispatch({ type: "retake" })}
          className={`mt-5 ${btnPrimary}`}
        >
          Retake the check
        </button>
      </div>
    );
  }

  const question = questions[state.index];
  const answered = state.picked !== null;
  const correct = answered && state.answers[state.answers.length - 1] === true;
  const correctText = question.options.find((o) => o.correct)?.text ?? "";
  const isLast = state.index + 1 >= questions.length;

  return (
    <div>
      <div className="flex items-center justify-between gap-3">
        <p className="font-mono text-[11px] text-ink-soft uppercase" data-testid="quiz-progress">
          Question {state.index + 1} of {questions.length}
        </p>
        <span className="rounded-full border border-line px-2.5 py-1 text-[10.5px] font-bold tracking-[0.1em] text-ink-soft uppercase">
          {KIND_LABELS[question.kind]}
        </span>
      </div>

      <p className="ky mt-3 text-lg">{question.question}</p>
      <div className="mt-3.5 grid gap-2">
        {question.options.map((o, i) => {
          let cls = "border-line bg-card hover:border-accent";
          let mark: string | null = null;
          let markCls = "";
          if (answered && o.correct) {
            cls = "border-green bg-green-soft";
            mark = "✓";
            markCls = "text-green";
          } else if (answered && i === state.picked) {
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
              data-testid="quick-check-option"
              disabled={answered}
              onClick={() => {
                dispatch({ type: "pick", option: i });
                onAnswered?.(question, o.correct);
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
        <div data-testid="quiz-explanation" className="mt-3">
          <p className={`text-[13.5px] font-semibold ${correct ? "text-green" : "text-accent"}`}>
            {correct ? "Yego! That's the one." : `Not quite — the answer is “${correctText}”.`}
          </p>
          {question.explanation ? (
            <p className="mt-1 text-[13.5px] leading-[1.6] text-ink-soft">
              {question.explanation}
            </p>
          ) : null}
          <button
            type="button"
            data-testid="quiz-next"
            onClick={() => dispatch({ type: "next" })}
            className={`mt-4 ${btnPrimary}`}
          >
            {isLast ? "See results →" : "Next question →"}
          </button>
        </div>
      ) : null}
    </div>
  );
}
