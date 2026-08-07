import type { QuizKind, QuizQuestion, RoadmapLesson } from "./api/types";

/**
 * Pure state + scoring for the lesson quiz ("question X of N" flow).
 * The React component dispatches into quizReducer; everything here is
 * side-effect free so vitest covers the flow without a DOM.
 */

export interface QuizState {
  /** 0-based index of the question on screen. */
  index: number;
  /** Option index picked for the current question; null = not yet answered. */
  picked: number | null;
  /** Correctness per answered question, in order. */
  answers: boolean[];
  /** True once the last question was advanced past — show the summary. */
  finished: boolean;
}

export const initialQuizState: QuizState = {
  index: 0,
  picked: null,
  answers: [],
  finished: false,
};

export type QuizAction =
  | { type: "pick"; option: number }
  | { type: "next" }
  | { type: "retake" };

export function quizReducer(
  questions: QuizQuestion[],
  state: QuizState,
  action: QuizAction,
): QuizState {
  switch (action.type) {
    case "pick": {
      // One answer per question — a second click on another option is a no-op.
      if (state.finished || state.picked !== null) return state;
      const question = questions[state.index];
      const correct = question?.options[action.option]?.correct === true;
      return { ...state, picked: action.option, answers: [...state.answers, correct] };
    }
    case "next": {
      if (state.finished || state.picked === null) return state;
      if (state.index + 1 >= questions.length) return { ...state, finished: true };
      return { ...state, index: state.index + 1, picked: null };
    }
    case "retake":
      return initialQuizState;
  }
}

export interface QuizKindScore {
  kind: QuizKind;
  correct: number;
  total: number;
}

export interface QuizSummary {
  total: number;
  correct: number;
  /** Per-kind breakdown, in first-appearance order. */
  byKind: QuizKindScore[];
}

export function summarizeQuiz(questions: QuizQuestion[], answers: boolean[]): QuizSummary {
  const byKind = new Map<QuizKind, QuizKindScore>();
  questions.forEach((q, i) => {
    const bucket = byKind.get(q.kind) ?? { kind: q.kind, correct: 0, total: 0 };
    bucket.total += 1;
    if (answers[i] === true) bucket.correct += 1;
    byKind.set(q.kind, bucket);
  });
  return {
    total: questions.length,
    correct: answers.filter(Boolean).length,
    byKind: [...byKind.values()],
  };
}

/**
 * The lesson's quiz in play order. Defensive rollout contract: when the
 * payload has no quiz yet, the legacy single quick_check becomes a
 * one-question quiz (the backend keeps quick_check = quiz[0] during rollout,
 * so both paths show the same first question).
 */
export function lessonQuiz(
  lesson: Pick<RoadmapLesson, "quiz" | "quick_check">,
): QuizQuestion[] {
  if (lesson.quiz && lesson.quiz.length > 0) {
    return [...lesson.quiz].sort((a, b) => a.ord - b.ord);
  }
  const qc = lesson.quick_check;
  if (!qc) return [];
  return [
    {
      ord: 1,
      kind: "vocab",
      question: qc.question,
      options: qc.options,
      explanation: "",
    },
  ];
}
