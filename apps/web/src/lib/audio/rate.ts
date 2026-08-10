/**
 * How fast the voices talk.
 *
 * `SLOW_RATE` is the one number every "listen slowed down" control in the app
 * uses. It is deliberately not lower: browsers time-stretch with
 * `preservesPitch` on (WSOLA in Chromium), which holds together well down to
 * ~0.7× on speech and starts smearing consonant transients below that — the
 * exact detail a learner is straining to hear. 0.7× buys ~43% more time
 * between syllables, which is what "say it slower" actually means here.
 *
 * A genuinely slower *synthesis* (server-side, engine speed parameter) would
 * beat time-stretching at any rate; see docs/frontend-notes.md.
 */
export const SLOW_RATE = 0.7;
export const NORMAL_RATE = 1;

/** Human label for the slow rate — used on buttons and captions. */
export const SLOW_RATE_LABEL = "0.7×";

/** localStorage key for the persisted "always play slowly" preference. */
export const SLOW_KEY = "sauti.audio.slow.v1";

/**
 * The stored preference. Anything other than an explicit "1" is OFF: full
 * speed is the default, because slowed audio is a crutch you reach for, not
 * the way the language is spoken.
 */
export function parseSlowPreference(raw: string | null | undefined): boolean {
  return raw === "1";
}

export function storedSlowPreference(on: boolean): string {
  return on ? "1" : "0";
}

/**
 * Rate for one play: an explicit `rate` (a screen that owns its own speed
 * control) wins, then this control's own `slow` flag, then the app-wide
 * preference.
 */
export function playbackRate({
  slow = false,
  alwaysSlow = false,
  rate,
}: {
  slow?: boolean;
  alwaysSlow?: boolean;
  rate?: number;
} = {}): number {
  if (typeof rate === "number") return rate;
  return slow || alwaysSlow ? SLOW_RATE : NORMAL_RATE;
}
