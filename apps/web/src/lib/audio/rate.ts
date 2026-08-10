/**
 * How fast the voices talk.
 *
 * `SLOW_RATE` is the one number every "listen slowed down" control in the app
 * uses. Browsers time-stretch with `preservesPitch` on (WSOLA in Chromium),
 * so the question was where that starts to sound broken. Measured against a
 * real Kinyarwanda clip from our own TTS, the timbre damage is flat from
 * 0.55× to 0.75× (~2.6 dB best-match spectral distance, i.e. a little better
 * than the same clip at 30 dB SNR) — there is no quality cliff in the range
 * anyone would want, so the rate is a teaching choice, not an audio one.
 *
 * 0.7× it is: ~43% more air between syllables, and the number the listening
 * player has advertised all along. If it still reads as fast, 0.6× costs
 * nothing measurable — this constant is the only place to change.
 *
 * The real fix is a genuinely slower *synthesis*: services/voice/tts_app.py
 * has no speed parameter yet, and an engine-level one would beat
 * time-stretching at any rate.
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
