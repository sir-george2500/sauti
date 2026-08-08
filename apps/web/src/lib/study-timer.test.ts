import { describe, expect, it } from "vitest";
import {
  clampGoal,
  dayKey,
  parseStored,
  stateForDay,
  tick,
  timerView,
} from "./study-timer";

describe("dayKey", () => {
  it("uses the local calendar day, not UTC", () => {
    // 23:30 local on the 8th stays the 8th even though UTC has rolled over.
    expect(dayKey(new Date(2026, 7, 8, 23, 30))).toBe("2026-08-08");
    expect(dayKey(new Date(2026, 0, 5, 0, 1))).toBe("2026-01-05");
  });
});

describe("clampGoal", () => {
  it("keeps goals inside 5–120 and rounds", () => {
    expect(clampGoal(15)).toBe(15);
    expect(clampGoal(1)).toBe(5);
    expect(clampGoal(500)).toBe(120);
    expect(clampGoal(14.6)).toBe(15);
    expect(clampGoal(NaN)).toBe(25);
  });
});

describe("stateForDay", () => {
  it("keeps today's progress and discards another day's", () => {
    const stored = { day: "2026-08-08", secondsDone: 300 };
    expect(stateForDay(stored, "2026-08-08")).toEqual(stored);
    expect(stateForDay(stored, "2026-08-09")).toEqual({ day: "2026-08-09", secondsDone: 0 });
    expect(stateForDay(null, "2026-08-09")).toEqual({ day: "2026-08-09", secondsDone: 0 });
  });
});

describe("tick", () => {
  const base = { day: "2026-08-08", secondsDone: 0 };

  it("accumulates seconds", () => {
    expect(tick(base, 5, 15).secondsDone).toBe(5);
    expect(tick(tick(base, 5, 15), 10, 15).secondsDone).toBe(15);
  });

  it("never exceeds the goal", () => {
    expect(tick({ day: base.day, secondsDone: 890 }, 30, 15).secondsDone).toBe(900);
  });

  it("ignores non-advancing ticks (backgrounded tab, clock skew)", () => {
    expect(tick(base, 0, 15)).toBe(base);
    expect(tick(base, -10, 15)).toBe(base);
  });
});

describe("timerView", () => {
  it("counts down from the goal", () => {
    const v = timerView({ day: "d", secondsDone: 0 }, 15);
    expect(v.remainingLabel).toBe("15:00");
    expect(v.progress).toBe(0);
    expect(v.done).toBe(false);
    expect(v.goalMinutes).toBe(15);
  });

  it("formats partial minutes and progress", () => {
    const v = timerView({ day: "d", secondsDone: 65 }, 15);
    expect(v.remainingLabel).toBe("13:55");
    expect(v.minutesDone).toBe(1);
    expect(v.progress).toBeCloseTo(65 / 900, 5);
  });

  it("reports done at the goal", () => {
    const v = timerView({ day: "d", secondsDone: 900 }, 15);
    expect(v.remainingLabel).toBe("00:00");
    expect(v.progress).toBe(1);
    expect(v.done).toBe(true);
  });
});

describe("parseStored", () => {
  it("round-trips valid state", () => {
    expect(parseStored(JSON.stringify({ day: "2026-08-08", secondsDone: 42 }))).toEqual({
      day: "2026-08-08",
      secondsDone: 42,
    });
  });

  it("rejects junk instead of throwing", () => {
    for (const bad of [null, "", "not json", "{}", '{"day":1}', '{"day":"d","secondsDone":-5}']) {
      expect(parseStored(bad)).toBeNull();
    }
  });
});
