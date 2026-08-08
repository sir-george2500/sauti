"use client";

import { useEffect, useRef, useState } from "react";
import { ttsUrl } from "@/lib/api/client";
import { playExclusive, stopPlayback } from "@/lib/audio/player";

/**
 * Play button for a curriculum item's native audio.
 *
 * When the payload carries a direct `src` (Cloudinary audio_url) it plays
 * that URL as-is — zero API hops, and usually already warm from the
 * per-lesson prefetch. Without `src` it falls back to GET /tts/{item_id}
 * (302 to the audio file).
 *
 * Mockup treatment: circular 1.5px-outlined button; idle shows the outline
 * colour glyph on transparent, playing fills the circle. `tone="gold"` is
 * the variant used on dark (bark) surfaces.
 *
 * Playback itself runs through the app's single audio channel
 * (`lib/audio/player`), so pressing one play button always silences another.
 */
export function AudioButton({
  itemId,
  src,
  label,
  slow = false,
  testid = "play-audio",
  tone = "accent",
  size = "md",
  className = "",
}: {
  itemId: string;
  /** Direct audio URL (item.audio_url) — preferred over the /tts route. */
  src?: string | null;
  label?: string;
  /** Playback at 0.65x for "listen slowed down". */
  slow?: boolean;
  testid?: string;
  tone?: "accent" | "gold";
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  // Identity for the shared channel, so this button only ever stops its own
  // clip — and so a source change (review flows reuse one instance across
  // cards) can't leave the previous card's audio running.
  const ownerRef = useRef({});
  const [playing, setPlaying] = useState(false);
  const url = src || ttsUrl(itemId);

  useEffect(() => {
    const owner = ownerRef.current;
    return () => {
      stopPlayback(owner);
      setPlaying(false);
    };
  }, [url]);

  const toggle = () => {
    if (playing) {
      stopPlayback(ownerRef.current);
      setPlaying(false);
      return;
    }
    setPlaying(true);
    void playExclusive(url, {
      owner: ownerRef.current,
      rate: slow ? 0.65 : 1,
      onStop: () => setPlaying(false),
    }).then((started) => {
      if (!started) setPlaying(false);
    });
  };

  const dim = size === "lg" ? "h-11 w-11" : size === "sm" ? "h-[34px] w-[34px]" : "h-9 w-9";
  const glyph = size === "lg" ? "h-3.5 w-3.5" : "h-3 w-3";
  const palette =
    tone === "gold"
      ? playing
        ? "border-gold bg-gold text-bark"
        : "border-gold bg-transparent text-gold hover:bg-gold/10"
      : playing
        ? "border-accent bg-accent text-on-accent"
        : "border-accent bg-transparent text-accent hover:bg-accent-soft";

  return (
    <button
      type="button"
      onClick={toggle}
      data-testid={testid}
      aria-label={label ?? (playing ? "Pause audio" : "Play audio")}
      className={`inline-flex shrink-0 cursor-pointer items-center justify-center rounded-full border-[1.5px] transition-colors ${dim} ${palette} ${className}`}
    >
      {playing ? (
        <svg viewBox="0 0 16 16" className={`fill-current ${glyph}`} aria-hidden>
          <rect x="3" y="3" width="10" height="10" rx="1" />
        </svg>
      ) : (
        <svg viewBox="0 0 16 16" className={`ml-0.5 fill-current ${glyph}`} aria-hidden>
          <path d="M4 2.5v11a.6.6 0 0 0 .92.5l8.4-5.5a.6.6 0 0 0 0-1L4.92 2a.6.6 0 0 0-.92.5Z" />
        </svg>
      )}
      {label ? <span className="sr-only">{label}</span> : null}
    </button>
  );
}
