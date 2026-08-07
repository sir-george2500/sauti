import { describe, expect, it } from "vitest";
import { lessonFromRoadmap } from "./endpoints";
import type { RoadmapLesson, RoadmapResponse, RoadmapStatus } from "./types";

/** Minimal roadmap: 2 levels / 3 units / 5 lessons, in course order. */
function lesson(id: string, status: RoadmapStatus): RoadmapLesson {
  return { id, title: `Lesson ${id}`, ord: Number(id.split("-")[1] ?? 1), status };
}

const roadmap: RoadmapResponse = {
  course_code: "KIN",
  levels: [
    {
      cefr: "A1",
      title: "Foundations",
      ord: 1,
      status: "current",
      units: [
        {
          id: "u1",
          title: "Greetings",
          situation_tag: "greetings",
          ord: 1,
          status: "current",
          lessons: [lesson("l1-1", "done"), lesson("l1-2", "current")],
        },
        {
          id: "u2",
          title: "Market",
          situation_tag: "market",
          ord: 2,
          status: "available",
          lessons: [lesson("l2-1", "available")],
        },
      ],
    },
    {
      cefr: "A2",
      title: "Daily life",
      ord: 2,
      status: "locked",
      units: [
        {
          id: "u3",
          title: "Travel",
          situation_tag: "travel",
          ord: 1,
          status: "locked",
          lessons: [lesson("l3-1", "locked"), lesson("l3-2", "locked")],
        },
      ],
    },
  ],
};

describe("lessonFromRoadmap prev/next derivation", () => {
  it("first lesson has no prev and points next at its unit sibling", () => {
    const view = lessonFromRoadmap(roadmap, "l1-1")!;
    expect(view.prev).toBeNull();
    expect(view.prev_lesson_id).toBeNull();
    expect(view.next_lesson_id).toBe("l1-2");
    expect(view.next).toMatchObject({ id: "l1-2", status: "current", label: "1.2" });
  });

  it("crosses a unit boundary: last lesson of unit 1 → first lesson of unit 2", () => {
    const view = lessonFromRoadmap(roadmap, "l1-2")!;
    expect(view.prev_lesson_id).toBe("l1-1");
    expect(view.prev).toMatchObject({ id: "l1-1", status: "done", label: "1.1" });
    expect(view.next_lesson_id).toBe("l2-1");
    expect(view.next).toMatchObject({ id: "l2-1", status: "available", label: "2.1" });
  });

  it("crosses a level boundary and carries the locked status for gating", () => {
    const view = lessonFromRoadmap(roadmap, "l2-1")!;
    expect(view.prev_lesson_id).toBe("l1-2");
    expect(view.next).toMatchObject({ id: "l3-1", status: "locked", label: "1.1" });
  });

  it("last lesson overall has no next", () => {
    const view = lessonFromRoadmap(roadmap, "l3-2")!;
    expect(view.prev_lesson_id).toBe("l3-1");
    expect(view.next).toBeNull();
    expect(view.next_lesson_id).toBeNull();
  });

  it("keeps the existing unit-scoped counters", () => {
    const view = lessonFromRoadmap(roadmap, "l1-2")!;
    expect(view.lessonNumber).toBe(2);
    expect(view.lessonCount).toBe(2);
    expect(view.unitTitle).toBe("Greetings");
    expect(view.levelCefr).toBe("A1");
  });

  it("returns null for an unknown lesson id", () => {
    expect(lessonFromRoadmap(roadmap, "nope")).toBeNull();
  });
});
