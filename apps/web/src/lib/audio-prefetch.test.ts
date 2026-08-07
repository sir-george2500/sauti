import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  _resetPrefetchCache,
  connectionAllowsPrefetch,
  PREFETCH_CAP,
  prefetchAudio,
} from "./audio-prefetch";

class FakeAudio {
  preload = "";
  loaded = false;
  src = "";
  constructor() {
    created.push(this);
  }
  load() {
    this.loaded = true;
  }
}

const created: FakeAudio[] = [];

describe("prefetchAudio", () => {
  beforeEach(() => {
    created.length = 0;
    _resetPrefetchCache();
    vi.stubGlobal("Audio", FakeAudio);
  });

  it("warms each url once with preload=auto, skipping null/undefined", () => {
    const n = prefetchAudio(["https://cdn/a.mp3", null, undefined, "https://cdn/b.mp3"]);
    expect(n).toBe(2);
    expect(created).toHaveLength(2);
    expect(created[0].preload).toBe("auto");
    expect(created[0].loaded).toBe(true);
  });

  it("dedupes across calls (revisiting a lesson costs nothing)", () => {
    prefetchAudio(["https://cdn/a.mp3"]);
    const n = prefetchAudio(["https://cdn/a.mp3", "https://cdn/c.mp3"]);
    expect(n).toBe(1);
    expect(created).toHaveLength(2);
  });

  it(`caps a single batch at ${PREFETCH_CAP}`, () => {
    const urls = Array.from({ length: 40 }, (_, i) => `https://cdn/${i}.mp3`);
    expect(prefetchAudio(urls)).toBe(PREFETCH_CAP);
    expect(created).toHaveLength(PREFETCH_CAP);
  });
});

describe("connectionAllowsPrefetch", () => {
  it("allows when the Network Information API is unsupported", () => {
    expect(connectionAllowsPrefetch(undefined)).toBe(true);
  });

  it("blocks Save-Data and 2g-class connections", () => {
    expect(connectionAllowsPrefetch({ saveData: true })).toBe(false);
    expect(connectionAllowsPrefetch({ effectiveType: "2g" })).toBe(false);
    expect(connectionAllowsPrefetch({ effectiveType: "slow-2g" })).toBe(false);
  });

  it("allows 3g/4g without Save-Data", () => {
    expect(connectionAllowsPrefetch({ effectiveType: "4g" })).toBe(true);
    expect(connectionAllowsPrefetch({ saveData: false, effectiveType: "3g" })).toBe(true);
  });
});
