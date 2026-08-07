import type { AttemptRequest, SrsGrade, SrsGradeLabel } from "./api/types";

/**
 * SRS review flow: the learner grades their own recall (again/hard/good/easy,
 * FSRS grades 1–4 per SPEC §4). The attempts endpoint (SPEC §5) accepts a
 * `score` float 0..1, so grades map onto evenly spaced scores — invertible on
 * the backend as grade = 1 + round(score * 3). Documented in
 * docs/frontend-notes.md.
 */

export const GRADE_LABELS: readonly SrsGradeLabel[] = ["again", "hard", "good", "easy"];

export function gradeFromLabel(label: SrsGradeLabel): SrsGrade {
  const idx = GRADE_LABELS.indexOf(label);
  if (idx === -1) throw new Error(`Unknown SRS grade label: ${label}`);
  return (idx + 1) as SrsGrade;
}

export function gradeToScore(grade: SrsGrade): number {
  return (grade - 1) / 3;
}

/** Build the POST /attempts payload for a graded SRS review of an item. */
export function reviewAttemptPayload(itemId: string, label: SrsGradeLabel): AttemptRequest {
  return {
    item_id: itemId,
    mode: "read",
    score: gradeToScore(gradeFromLabel(label)),
  };
}
