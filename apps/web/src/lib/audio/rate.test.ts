import { describe, expect, it } from "vitest";
import { NORMAL_RATE, parseSlowPreference, playbackRate, SLOW_RATE } from "./rate";

describe("parseSlowPreference", () => {
  it("is off unless the stored value is an explicit yes", () => {
    expect(parseSlowPreference(null)).toBe(false);
    expect(parseSlowPreference(undefined)).toBe(false);
    expect(parseSlowPreference("0")).toBe(false);
    expect(parseSlowPreference("true")).toBe(false);
    expect(parseSlowPreference("")).toBe(false);
    expect(parseSlowPreference("1")).toBe(true);
  });
});

describe("playbackRate", () => {
  it("is full speed by default", () => {
    expect(playbackRate()).toBe(NORMAL_RATE);
    expect(playbackRate({})).toBe(NORMAL_RATE);
  });

  it("slows a control that asks for it", () => {
    expect(playbackRate({ slow: true })).toBe(SLOW_RATE);
  });

  it("slows every control while the app-wide preference is on", () => {
    expect(playbackRate({ alwaysSlow: true })).toBe(SLOW_RATE);
  });

  it("lets a screen with its own speed control override both", () => {
    // The listening player's "1× street" must stay 1× even with the
    // preference on, or its own label would be a lie.
    expect(playbackRate({ alwaysSlow: true, rate: NORMAL_RATE })).toBe(NORMAL_RATE);
    expect(playbackRate({ slow: true, rate: NORMAL_RATE })).toBe(NORMAL_RATE);
  });

  it("keeps the slow rate inside the range time-stretching survives", () => {
    expect(SLOW_RATE).toBeGreaterThanOrEqual(0.6);
    expect(SLOW_RATE).toBeLessThanOrEqual(0.75);
  });
});
