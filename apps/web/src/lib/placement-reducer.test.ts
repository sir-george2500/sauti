import { describe, expect, it } from "vitest";
import {
  placementInitialState,
  placementReducer,
  type PlacementState,
} from "./placement-reducer";
import type { PlacementQuestion } from "./api/types";

const Q1: PlacementQuestion = {
  item_id: "item-1",
  prompt: "Someone greets you: “Amakuru?” — choose the natural reply.",
  options: ["Ni meza!", "Murakoze.", "Yego."],
  number: 1,
};

const Q2: PlacementQuestion = {
  item_id: "item-2",
  prompt: "One child is umwana. Several children are…",
  options: ["abana", "imyana", "utwana"],
  number: 2,
};

function questionState(): Extract<PlacementState, { phase: "question" }> {
  let s = placementReducer(placementInitialState, { type: "START" });
  s = placementReducer(s, { type: "START_SUCCESS", sessionId: "sess-1", question: Q1 });
  if (s.phase !== "question") throw new Error("expected question phase");
  return s;
}

describe("placement flow reducer", () => {
  it("walks intro → starting → question", () => {
    const starting = placementReducer(placementInitialState, { type: "START" });
    expect(starting).toEqual({ phase: "starting", error: null });

    const question = placementReducer(starting, {
      type: "START_SUCCESS",
      sessionId: "sess-1",
      question: Q1,
    });
    expect(question).toMatchObject({
      phase: "question",
      sessionId: "sess-1",
      question: Q1,
      answered: 0,
      selected: null,
      submitting: false,
    });
  });

  it("records a selection and submits it", () => {
    let s: PlacementState = questionState();
    s = placementReducer(s, { type: "SELECT", option: "Ni meza!" });
    expect(s).toMatchObject({ selected: "Ni meza!" });
    s = placementReducer(s, { type: "SUBMIT" });
    expect(s).toMatchObject({ submitting: true });
  });

  it("ignores SUBMIT without a selection and SELECT while submitting", () => {
    const s = questionState();
    expect(placementReducer(s, { type: "SUBMIT" })).toBe(s);

    let submitting = placementReducer(s, { type: "SELECT", option: "Yego." });
    submitting = placementReducer(submitting, { type: "SUBMIT" });
    expect(placementReducer(submitting, { type: "SELECT", option: "Murakoze." })).toBe(
      submitting,
    );
  });

  it("advances to the next question and counts answers", () => {
    let s: PlacementState = questionState();
    s = placementReducer(s, { type: "SELECT", option: "Ni meza!" });
    s = placementReducer(s, { type: "SUBMIT" });
    s = placementReducer(s, { type: "ANSWER_SUCCESS", response: { question: Q2 } });
    expect(s).toMatchObject({
      phase: "question",
      question: Q2,
      answered: 1,
      selected: null,
      submitting: false,
    });
  });

  it("finishes when the server places a level", () => {
    let s: PlacementState = questionState();
    s = placementReducer(s, { type: "SELECT", option: "Ni meza!" });
    s = placementReducer(s, { type: "SUBMIT" });
    s = placementReducer(s, {
      type: "ANSWER_SUCCESS",
      response: { result: "Solid A2 — market-ready.", placed_level: "A2" },
    });
    expect(s).toEqual({
      phase: "result",
      placedLevel: "A2",
      result: "Solid A2 — market-ready.",
    });
  });

  it("surfaces an error on a malformed answer response", () => {
    let s: PlacementState = questionState();
    s = placementReducer(s, { type: "SELECT", option: "Yego." });
    s = placementReducer(s, { type: "SUBMIT" });
    s = placementReducer(s, { type: "ANSWER_SUCCESS", response: {} });
    expect(s).toMatchObject({
      phase: "question",
      submitting: false,
      error: expect.stringContaining("unexpected"),
    });
  });

  it("returns to intro with a message when starting fails", () => {
    const starting = placementReducer(placementInitialState, { type: "START" });
    const failed = placementReducer(starting, { type: "FAIL", message: "offline" });
    expect(failed).toEqual({ phase: "intro", error: "offline" });
  });

  it("keeps the question but clears submitting when an answer fails", () => {
    let s: PlacementState = questionState();
    s = placementReducer(s, { type: "SELECT", option: "Yego." });
    s = placementReducer(s, { type: "SUBMIT" });
    s = placementReducer(s, { type: "FAIL", message: "network" });
    expect(s).toMatchObject({
      phase: "question",
      question: Q1,
      submitting: false,
      error: "network",
    });
  });

  it("is inert after the result is reached", () => {
    let s: PlacementState = questionState();
    s = placementReducer(s, { type: "SELECT", option: "Ni meza!" });
    s = placementReducer(s, { type: "SUBMIT" });
    s = placementReducer(s, {
      type: "ANSWER_SUCCESS",
      response: { placed_level: "A1" },
    });
    expect(placementReducer(s, { type: "START" })).toBe(s);
    expect(placementReducer(s, { type: "FAIL", message: "x" })).toBe(s);
  });
});
