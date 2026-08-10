import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { AudioButton, AudioControls } from "./AudioButton";
import { NORMAL_RATE, SLOW_KEY, SLOW_RATE } from "@/lib/audio/rate";

/** Every clip handed to the browser, in order, with the rate it played at. */
const played: { src: string; rate: number }[] = [];

class FakeAudio {
  src: string;
  playbackRate = 1;
  constructor(src: string) {
    this.src = src;
  }
  addEventListener() {}
  play() {
    // The player sets playbackRate before calling play(), so this is the rate
    // the learner actually hears.
    played.push({ src: this.src, rate: this.playbackRate });
    return Promise.resolve();
  }
  pause() {}
}

const urls = () => played.map((p) => p.src);

describe("AudioButton", () => {
  beforeEach(() => {
    played.length = 0;
    window.localStorage.clear();
    vi.stubGlobal("Audio", FakeAudio);
  });

  it("plays the item's own audio after the itemId prop changes (review-flow card advance)", () => {
    const { rerender } = render(<AudioButton itemId="item-1" />);
    fireEvent.click(screen.getByTestId("play-audio"));
    expect(played).toHaveLength(1);
    expect(urls()[0]).toContain("item-1");

    // Same component instance, next card — must NOT replay item-1's element.
    rerender(<AudioButton itemId="item-2" />);
    fireEvent.click(screen.getByTestId("play-audio")); // pause (state kept "playing"): resets
    fireEvent.click(screen.getByTestId("play-audio"));
    expect(urls().join(" ")).toContain("item-2");
    expect(urls().filter((u) => u.includes("item-1"))).toHaveLength(1);
  });

  it("plays a direct src (audio_url) instead of the /tts route when provided", () => {
    render(<AudioButton itemId="item-1" src="https://cdn.example/kin/muraho.mp3" />);
    fireEvent.click(screen.getByTestId("play-audio"));
    expect(urls()).toEqual(["https://cdn.example/kin/muraho.mp3"]);
  });

  it("falls back to the /tts route when src is null (rollout gap)", () => {
    render(<AudioButton itemId="item-9" src={null} />);
    fireEvent.click(screen.getByTestId("play-audio"));
    expect(played).toHaveLength(1);
    expect(urls()[0]).toContain("/tts/item-9");
  });

  it("plays at full speed by default and at the slow rate when asked", () => {
    const { rerender } = render(<AudioButton itemId="item-1" />);
    fireEvent.click(screen.getByTestId("play-audio"));
    expect(played[0].rate).toBe(NORMAL_RATE);

    rerender(<AudioButton itemId="item-1" slow />);
    fireEvent.click(screen.getByTestId("play-audio")); // stop
    fireEvent.click(screen.getByTestId("play-audio"));
    expect(played[1].rate).toBe(SLOW_RATE);
  });

  it("plays a plain play button slowly while the saved preference is on", () => {
    window.localStorage.setItem(SLOW_KEY, "1");
    render(<AudioButton itemId="item-1" />);
    fireEvent.click(screen.getByTestId("play-audio"));
    expect(played[0].rate).toBe(SLOW_RATE);
  });

  it("lets an explicit rate beat the preference (a screen with its own speed control)", () => {
    window.localStorage.setItem(SLOW_KEY, "1");
    render(<AudioButton itemId="item-1" rate={NORMAL_RATE} />);
    fireEvent.click(screen.getByTestId("play-audio"));
    expect(played[0].rate).toBe(NORMAL_RATE);
  });
});

describe("AudioControls", () => {
  beforeEach(() => {
    played.length = 0;
    window.localStorage.clear();
    vi.stubGlobal("Audio", FakeAudio);
  });

  it("offers a slow companion to the play button, on the same clip", () => {
    render(<AudioControls itemId="item-1" src="https://cdn.example/a.mp3" label="Play “Muraho”" />);

    fireEvent.click(screen.getByTestId("play-audio"));
    fireEvent.click(screen.getByTestId("play-slow"));

    expect(played).toEqual([
      { src: "https://cdn.example/a.mp3", rate: NORMAL_RATE },
      { src: "https://cdn.example/a.mp3", rate: SLOW_RATE },
    ]);
    expect(screen.getByTestId("play-slow")).toHaveAttribute(
      "aria-label",
      "Play “Muraho” slowly",
    );
  });
});
