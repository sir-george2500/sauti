"use client";

import { useEffect, useRef, useState } from "react";
import { ttsUrl } from "@/lib/api/client";

/**
 * Play button for a curriculum item's native audio via GET /tts/{item_id}
 * (302 to the audio file — stub silence in MVP, shape final).
 *
 * Mockup treatment: circular 1.5px-outlined button; idle shows the outline
 * colour glyph on transparent, playing fills the circle. `tone="gold"` is
 * the variant used on dark (bark) surfaces.
 */
export function AudioButton({
  itemId,
  label,
  slow = false,
  testid = "play-audio",
  tone = "accent",
  size = "md",
  className = "",
}: {
  itemId: string;
  label?: string;
  /** Playback at 0.65x for "listen slowed down". */
  slow?: boolean;
  testid?: string;
  tone?: "accent" | "gold";
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    return () => {
      audioRef.current?.pause();
      audioRef.current = null;
    };
  }, []);

  const toggle = () => {
    if (playing) {
      audioRef.current?.pause();
      setPlaying(false);
      return;
    }
    if (!audioRef.current) {
      const audio = new Audio(ttsUrl(itemId));
      audio.addEventListener("ended", () => setPlaying(false));
      audio.addEventListener("error", () => setPlaying(false));
      audioRef.current = audio;
    }
    audioRef.current.playbackRate = slow ? 0.65 : 1;
    void audioRef.current.play().catch(() => setPlaying(false));
    setPlaying(true);
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
