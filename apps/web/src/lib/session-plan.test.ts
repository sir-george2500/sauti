import { describe, expect, it } from "vitest";
import { blockHref, consistencyLabel, sessionPlanView } from "./session-plan";
import type { SessionPlan } from "./api/types";

const PLAN: SessionPlan = {
  total_min: 25,
  blocks: [
    {
      tag: "REVIEW",
      mins: 8,
      title: "Market words, resurfacing",
      sub: "9 sentences due",
      kind: "review",
      ref_id: "market",
    },
    {
      tag: "LESSON",
      mins: 10,
      title: "Noun classes: talking about people",
      sub: "umu-/aba- and friends",
      kind: "lesson",
      ref_id: "lesson-7",
    },
    {
      tag: "SPEAK",
      mins: 7,
      title: "Amakuru yawe?",
      sub: "tone on KU",
      kind: "speak",
      ref_id: "item-3",
    },
  ],
};

describe("session plan rendering logic", () => {
  it("routes each block kind to its practice surface", () => {
    expect(blockHref({ kind: "review", ref_id: "market" })).toBe("/vocab/market");
    expect(blockHref({ kind: "lesson", ref_id: "lesson-7" })).toBe("/lesson/lesson-7");
    expect(blockHref({ kind: "speak", ref_id: "item-3" })).toBe(
      "/practice/pronunciation/item-3",
    );
  });

  it("falls back to the deck index when a review block has no ref", () => {
    expect(blockHref({ kind: "review", ref_id: "" })).toBe("/vocab");
  });

  it("URL-encodes situation tags", () => {
    expect(blockHref({ kind: "review", ref_id: "market & money" })).toBe(
      "/vocab/market%20%26%20money",
    );
  });

  it("builds the display model with hrefs, total and count label", () => {
    const view = sessionPlanView(PLAN);
    expect(view.totalMin).toBe(25);
    expect(view.blockCountLabel).toBe("three short blocks");
    expect(view.blocks.map((b) => b.href)).toEqual([
      "/vocab/market",
      "/lesson/lesson-7",
      "/practice/pronunciation/item-3",
    ]);
    expect(view.blocks[0]).toMatchObject({ tag: "REVIEW", mins: 8, kind: "review" });
  });

  it("starts the session at the first block", () => {
    expect(sessionPlanView(PLAN).startHref).toBe("/vocab/market");
  });

  it("handles a single-block plan and an empty plan", () => {
    const single = sessionPlanView({ total_min: 10, blocks: [PLAN.blocks[1]] });
    expect(single.blockCountLabel).toBe("one short block");
    expect(single.startHref).toBe("/lesson/lesson-7");

    const empty = sessionPlanView({ total_min: 0, blocks: [] });
    expect(empty.blockCountLabel).toBe("no short blocks");
    expect(empty.startHref).toBe("/roadmap");
  });

  it("formats consistency in the product's voice", () => {
    expect(consistencyLabel(12, 14)).toBe("12 of the last 14 days");
  });
});
