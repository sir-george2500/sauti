import { describe, expect, it } from "vitest";
import { GRADE_LABELS, gradeFromLabel, gradeToScore, reviewAttemptPayload } from "./srs";
import type { SrsGrade } from "./api/types";

describe("SRS grade → attempt payload mapping", () => {
  it("maps labels to FSRS grades 1–4", () => {
    expect(gradeFromLabel("again")).toBe(1);
    expect(gradeFromLabel("hard")).toBe(2);
    expect(gradeFromLabel("good")).toBe(3);
    expect(gradeFromLabel("easy")).toBe(4);
  });

  it("maps grades to evenly spaced scores in 0..1", () => {
    expect(gradeToScore(1)).toBe(0);
    expect(gradeToScore(2)).toBeCloseTo(1 / 3);
    expect(gradeToScore(3)).toBeCloseTo(2 / 3);
    expect(gradeToScore(4)).toBe(1);
  });

  it("is invertible on the backend as grade = 1 + round(score * 3)", () => {
    for (const label of GRADE_LABELS) {
      const grade = gradeFromLabel(label);
      const score = gradeToScore(grade);
      expect(1 + Math.round(score * 3)).toBe(grade);
    }
  });

  it("builds a read-mode attempt for the reviewed item", () => {
    expect(reviewAttemptPayload("item-42", "good")).toEqual({
      item_id: "item-42",
      mode: "read",
      score: 2 / 3,
    });
    expect(reviewAttemptPayload("item-42", "again")).toEqual({
      item_id: "item-42",
      mode: "read",
      score: 0,
    });
  });

  it("rejects unknown labels", () => {
    expect(() => gradeFromLabel("perfect" as never)).toThrow(/Unknown SRS grade label/);
  });

  it("keeps scores within the API's 0..1 contract", () => {
    for (let g = 1 as SrsGrade; g <= 4; g++) {
      const score = gradeToScore(g as SrsGrade);
      expect(score).toBeGreaterThanOrEqual(0);
      expect(score).toBeLessThanOrEqual(1);
    }
  });
});
