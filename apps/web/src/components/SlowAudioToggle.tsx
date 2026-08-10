"use client";

import { TurtleGlyph } from "@/components/AudioButton";
import { SLOW_RATE_LABEL } from "@/lib/audio/rate";
import { setSlowAudio, useSlowAudio } from "@/lib/audio/rate-store";

/**
 * "Always play slowly" — one switch for every voice in the app.
 *
 * It lives in the sidebar footer next to the rhythm pill: this is a standing
 * preference about how the app sounds, not a per-clip choice, and the footer
 * is where the app already keeps standing things about you. Off by default;
 * the per-clip turtle beside each play button stays there either way, for the
 * one line you want to hear again slowly.
 *
 * Persisted in localStorage, so it survives a reload — the learner sets it
 * once, in week one, and forgets it exists.
 */
export function SlowAudioToggle({
  testid = "slow-audio-toggle",
  compact = false,
  className = "",
}: {
  /** Omitted on the mobile bar so the sidebar keeps the unique testid. */
  testid?: string;
  /** Glyph + rate only — for the cramped mobile top bar. */
  compact?: boolean;
  className?: string;
}) {
  const on = useSlowAudio();

  return (
    <button
      type="button"
      data-testid={testid}
      data-on={on}
      aria-pressed={on}
      onClick={() => setSlowAudio(!on)}
      title={
        on
          ? `Every clip plays at ${SLOW_RATE_LABEL} — tap for full speed`
          : `Play every clip at ${SLOW_RATE_LABEL} until you turn this off`
      }
      className={`flex w-full cursor-pointer items-center gap-2 rounded-full border py-[7px] pr-3 pl-3 transition-colors ${
        on
          ? "border-rhythm-line bg-rhythm-bg text-rhythm-text"
          : "border-bark-line bg-transparent text-bark-mute hover:text-bark-glow"
      } ${className}`}
    >
      <TurtleGlyph className="h-3.5 w-[17px] flex-none" />
      {compact ? null : <span className="text-xs font-semibold">Slow speech</span>}
      <span className="ml-auto font-mono text-[10px] uppercase">
        {on ? SLOW_RATE_LABEL : "Off"}
      </span>
    </button>
  );
}
