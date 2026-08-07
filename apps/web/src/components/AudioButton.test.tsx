import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { AudioButton } from "./AudioButton";

/** Every URL handed to `new Audio(...)`, in order. */
const created: string[] = [];

class FakeAudio {
  src: string;
  playbackRate = 1;
  constructor(src: string) {
    this.src = src;
    created.push(src);
  }
  addEventListener() {}
  play() {
    return Promise.resolve();
  }
  pause() {}
}

describe("AudioButton", () => {
  beforeEach(() => {
    created.length = 0;
    vi.stubGlobal("Audio", FakeAudio);
  });

  it("plays the item's own audio after the itemId prop changes (review-flow card advance)", () => {
    const { rerender } = render(<AudioButton itemId="item-1" />);
    fireEvent.click(screen.getByTestId("play-audio"));
    expect(created).toHaveLength(1);
    expect(created[0]).toContain("item-1");

    // Same component instance, next card — must NOT replay item-1's element.
    rerender(<AudioButton itemId="item-2" />);
    fireEvent.click(screen.getByTestId("play-audio")); // pause (state kept "playing"): resets
    fireEvent.click(screen.getByTestId("play-audio"));
    const urls = created.join(" ");
    expect(urls).toContain("item-2");
    expect(created.filter((u) => u.includes("item-1"))).toHaveLength(1);
  });
});
