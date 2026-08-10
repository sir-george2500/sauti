"use client";

import { useEffect, useRef, useState } from "react";
import { ttsUrl } from "@/lib/api/client";
import { playExclusive, stopPlayback } from "@/lib/audio/player";
import { playbackRate, SLOW_RATE_LABEL } from "@/lib/audio/rate";
import { useSlowAudio } from "@/lib/audio/rate-store";

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
 *
 * Speed: `slow` plays this control at SLOW_RATE; otherwise the app-wide
 * "always play slowly" preference decides. A screen that owns its own speed
 * control passes an explicit `rate`, which beats both.
 */

const DIM = {
  xs: "h-7 w-7",
  sm: "h-[34px] w-[34px]",
  md: "h-9 w-9",
  lg: "h-11 w-11",
} as const;

const GLYPH = {
  xs: "h-2.5 w-2.5",
  sm: "h-3 w-3",
  md: "h-3 w-3",
  lg: "h-3.5 w-3.5",
} as const;

const TURTLE = {
  xs: "h-3.5 w-[17px]",
  sm: "h-4 w-5",
  md: "h-4 w-5",
  lg: "h-[18px] w-[22px]",
} as const;

type Size = keyof typeof DIM;

/**
 * The universal "slower" mark. A turtle reads as speed at a glance in a
 * 28px circle where "0.7×" would not fit — the rate itself lives in the
 * tooltip and the accessible name.
 */
export function TurtleGlyph({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 20 16" className={`fill-current ${className}`} aria-hidden>
      {/* shell */}
      <path d="M3.4 11.1a5.3 5.3 0 0 1 10.6 0Z" />
      {/* head */}
      <path d="M13.6 9.4h1.2a1.7 1.7 0 1 1 0 3 1.7 1.7 0 0 1-1.6-1.2Z" />
      {/* feet */}
      <rect x="4.3" y="11.1" width="2.7" height="2" rx="1" />
      <rect x="10.6" y="11.1" width="2.7" height="2" rx="1" />
      {/* tail */}
      <path d="M3.4 11.1 1 11.9l2.4 1.1Z" />
    </svg>
  );
}

function paletteFor(
  tone: "accent" | "gold",
  variant: "solid" | "quiet",
  playing: boolean,
  active: boolean,
): string {
  if (tone === "gold") {
    if (playing) return "border-gold bg-gold text-bark";
    if (variant === "quiet") {
      return active
        ? "border-gold bg-gold/15 text-gold"
        : "border-bark-line bg-transparent text-bark-mute hover:border-gold hover:text-gold";
    }
    return "border-gold bg-transparent text-gold hover:bg-gold/10";
  }
  if (playing) return "border-accent bg-accent text-on-accent";
  if (variant === "quiet") {
    return active
      ? "border-accent bg-accent-soft text-accent"
      : "border-line-strong bg-transparent text-ink-faint hover:border-accent hover:text-accent";
  }
  return "border-accent bg-transparent text-accent hover:bg-accent-soft";
}

export function AudioButton({
  itemId,
  src,
  label,
  slow = false,
  rate,
  testid = "play-audio",
  tone = "accent",
  size = "md",
  variant = "solid",
  glyph = "play",
  title,
  className = "",
}: {
  /** Curriculum item id — only needed for the /tts fallback. */
  itemId?: string;
  /** Direct audio URL (item.audio_url) — preferred over the /tts route. */
  src?: string | null;
  label?: string;
  /** Play this control at the slow rate ("listen slowed down"). */
  slow?: boolean;
  /** Explicit rate — for screens with their own speed control. */
  rate?: number;
  testid?: string;
  tone?: "accent" | "gold";
  size?: Size;
  /** `quiet` is the secondary treatment used by the slow control. */
  variant?: "solid" | "quiet";
  glyph?: "play" | "turtle";
  title?: string;
  className?: string;
}) {
  // Identity for the shared channel, so this button only ever stops its own
  // clip — and so a source change (review flows reuse one instance across
  // cards) can't leave the previous card's audio running.
  const ownerRef = useRef({});
  const [playing, setPlaying] = useState(false);
  const alwaysSlow = useSlowAudio();
  const url = src || (itemId ? ttsUrl(itemId) : "");

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
      rate: playbackRate({ slow, alwaysSlow, rate }),
      onStop: () => setPlaying(false),
    }).then((started) => {
      if (!started) setPlaying(false);
    });
  };

  // A slow control lights up while the app-wide preference is on: it is
  // already what the plain play button does, and saying so beats leaving two
  // buttons that look different and behave the same.
  const active = slow && alwaysSlow;
  const dim = DIM[size];
  const palette = paletteFor(tone, variant, playing, active);
  const name =
    label ?? (playing ? "Pause audio" : glyph === "turtle" ? "Play slowly" : "Play audio");

  return (
    <button
      type="button"
      onClick={toggle}
      data-testid={testid}
      aria-label={name}
      title={title}
      className={`inline-flex shrink-0 cursor-pointer items-center justify-center rounded-full border-[1.5px] transition-colors ${dim} ${palette} ${className}`}
    >
      {playing ? (
        <svg viewBox="0 0 16 16" className={`fill-current ${GLYPH[size]}`} aria-hidden>
          <rect x="3" y="3" width="10" height="10" rx="1" />
        </svg>
      ) : glyph === "turtle" ? (
        <TurtleGlyph className={TURTLE[size]} />
      ) : (
        <svg viewBox="0 0 16 16" className={`ml-0.5 fill-current ${GLYPH[size]}`} aria-hidden>
          <path d="M4 2.5v11a.6.6 0 0 0 .92.5l8.4-5.5a.6.6 0 0 0 0-1L4.92 2a.6.6 0 0 0-.92.5Z" />
        </svg>
      )}
      {label ? <span className="sr-only">{label}</span> : null}
    </button>
  );
}

/**
 * Play + "slower" as a pair — the standard treatment wherever the app speaks
 * Kinyarwanda.
 *
 * Two visible buttons rather than a hidden long-press: a long-press is
 * undiscoverable, has no desktop equivalent, and fights the browser's own
 * context menu. The slow one is deliberately smaller, outlined in the quiet
 * palette and glyph-only, so it reads as a companion to the play button
 * instead of a second thing to decide about.
 */
export function AudioControls({
  itemId,
  src,
  label,
  testid = "play-audio",
  slowTestid = "play-slow",
  tone = "accent",
  size = "md",
  className = "",
}: {
  itemId?: string;
  src?: string | null;
  /** Accessible name of the play button; the slow one appends "slowly". */
  label?: string;
  testid?: string;
  slowTestid?: string;
  tone?: "accent" | "gold";
  size?: Size;
  className?: string;
}) {
  return (
    <span className={`inline-flex flex-none items-center gap-1.5 ${className}`}>
      <AudioButton
        itemId={itemId}
        src={src}
        label={label}
        testid={testid}
        tone={tone}
        size={size}
      />
      <AudioButton
        itemId={itemId}
        src={src}
        slow
        glyph="turtle"
        variant="quiet"
        size="xs"
        tone={tone}
        testid={slowTestid}
        label={label ? `${label} slowly` : "Play slowly"}
        title={`Slower — ${SLOW_RATE_LABEL}`}
      />
    </span>
  );
}
