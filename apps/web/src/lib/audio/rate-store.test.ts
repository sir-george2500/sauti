import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { SLOW_KEY } from "./rate";
import { setSlowAudio, useSlowAudio } from "./rate-store";

describe("slow-audio preference store", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("defaults to off", () => {
    const { result } = renderHook(() => useSlowAudio());
    expect(result.current).toBe(false);
  });

  it("reads a preference saved by an earlier session", () => {
    window.localStorage.setItem(SLOW_KEY, "1");
    const { result } = renderHook(() => useSlowAudio());
    expect(result.current).toBe(true);
  });

  it("persists a flip and pushes it to every subscriber", () => {
    const a = renderHook(() => useSlowAudio());
    const b = renderHook(() => useSlowAudio());

    act(() => setSlowAudio(true));
    expect(window.localStorage.getItem(SLOW_KEY)).toBe("1");
    expect(a.result.current).toBe(true);
    expect(b.result.current).toBe(true);

    act(() => setSlowAudio(false));
    expect(window.localStorage.getItem(SLOW_KEY)).toBe("0");
    expect(a.result.current).toBe(false);
  });

  it("follows a change made in another tab", () => {
    const { result } = renderHook(() => useSlowAudio());
    act(() => {
      window.localStorage.setItem(SLOW_KEY, "1");
      window.dispatchEvent(new StorageEvent("storage", { key: SLOW_KEY }));
    });
    expect(result.current).toBe(true);
  });
});
