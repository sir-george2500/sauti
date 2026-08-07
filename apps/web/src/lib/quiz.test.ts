import { describe, expect, it } from "vitest";
import type { QuizQuestion } from "./api/types";
import {
  initialQuizState,
  lessonQuiz,
  quizReducer,
  summarizeQuiz,
  type QuizState,
} from "./quiz";

function q(
  ord: number,
  kind: QuizQuestion["kind"],
  correctIndex = 0,
  itemId?: string,
): QuizQuestion {
  return {
    ord,
    kind,
    question: `Q${ord}?`,
    options: [
      { text: `${ord}-a`, correct: correctIndex === 0 },
      { text: `${ord}-b`, correct: correctIndex === 1 },
      { text: `${ord}-c`, correct: correctIndex === 2 },
    ],
    explanation: `Because ${ord}.`,
    item_id: itemId ?? null,
  };
}

const questions = [q(1, "grammar"), q(2, "vocab", 1), q(3, "usage"), q(4, "grammar")];
const step = (s: QuizState, a: Parameters<typeof quizReducer>[2]) =>
  quizReducer(questions, s, a);

describe("quizReducer", () => {
  it("records correctness on pick and locks the question", () => {
    const picked = step(initialQuizState, { type: "pick", option: 0 });
    expect(picked.picked).toBe(0);
    expect(picked.answers).toEqual([true]);
    // second pick on the same question is a no-op (one attempt per question)
    expect(step(picked, { type: "pick", option: 1 })).toBe(picked);
  });

  it("records a wrong pick as false", () => {
    const picked = step(initialQuizState, { type: "pick", option: 2 });
    expect(picked.answers).toEqual([false]);
  });

  it("ignores next before an answer", () => {
    expect(step(initialQuizState, { type: "next" })).toBe(initialQuizState);
  });

  it("advances and clears the pick, finishing after the last question", () => {
    let s = initialQuizState;
    for (let i = 0; i < questions.length; i++) {
      s = step(s, { type: "pick", option: i === 1 ? 1 : 0 }); // all correct
      const wasLast = i === questions.length - 1;
      s = step(s, { type: "next" });
      if (!wasLast) {
        expect(s.index).toBe(i + 1);
        expect(s.picked).toBeNull();
        expect(s.finished).toBe(false);
      }
    }
    expect(s.finished).toBe(true);
    expect(s.answers).toEqual([true, true, true, true]);
  });

  it("retake resets to the first question with a clean slate", () => {
    let s = step(initialQuizState, { type: "pick", option: 1 });
    s = step(s, { type: "next" });
    s = step(s, { type: "retake" });
    expect(s).toEqual(initialQuizState);
  });
});

describe("summarizeQuiz", () => {
  it("totals and breaks scores down per kind", () => {
    const summary = summarizeQuiz(questions, [true, false, true, true]);
    expect(summary.total).toBe(4);
    expect(summary.correct).toBe(3);
    expect(summary.byKind).toEqual([
      { kind: "grammar", correct: 2, total: 2 },
      { kind: "vocab", correct: 0, total: 1 },
      { kind: "usage", correct: 1, total: 1 },
    ]);
  });
});

describe("lessonQuiz (rollout fallback)", () => {
  it("uses quiz[] when present, sorted by ord", () => {
    const out = lessonQuiz({ quiz: [q(2, "vocab"), q(1, "grammar")], quick_check: null });
    expect(out.map((x) => x.ord)).toEqual([1, 2]);
  });

  it("falls back to the single quick_check when quiz is absent or empty", () => {
    const quick_check = {
      question: "What does “Muraho” mean?",
      options: [
        { text: "Hello", correct: true },
        { text: "Goodbye", correct: false },
      ],
    };
    for (const quiz of [undefined, null, []]) {
      const out = lessonQuiz({ quiz, quick_check });
      expect(out).toHaveLength(1);
      expect(out[0].question).toBe(quick_check.question);
      expect(out[0].options).toEqual(quick_check.options);
    }
  });

  it("returns [] when the lesson has neither", () => {
    expect(lessonQuiz({})).toEqual([]);
  });
});
