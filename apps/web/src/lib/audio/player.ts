"use client";

/**
 * One voice at a time.
 *
 * Every play control in the app (lesson audio, a conversation turn, a Mwarimu
 * reply) goes through this single channel, so starting a clip always stops
 * whatever was already talking — two Kinyarwanda sentences over each other are
 * useless to a learner.
 *
 * The `owner` tag lets a component stop only *its* clip (the buddy panel
 * closing must not cut off a lesson item that some other screen started).
 *
 * `play()` returns a promise that REJECTS when the browser blocks autoplay —
 * a completely normal outcome on a page the learner hasn't clicked yet. That
 * rejection is swallowed here and reported as `false`, so callers fall back to
 * their idle "tap to play" state instead of spraying the console.
 */

let currentAudio: HTMLAudioElement | null = null;
let currentOwner: unknown = null;
let currentOnStop: (() => void) | null = null;

function forget() {
  currentAudio = null;
  currentOwner = null;
  currentOnStop = null;
}

const ANY_OWNER = Symbol("any-owner");

/**
 * Stop playback and tell its owner. With an `owner` argument this is a no-op
 * unless that owner is the one currently playing.
 */
export function stopPlayback(owner: unknown = ANY_OWNER): void {
  if (!currentAudio) return;
  if (owner !== ANY_OWNER && currentOwner !== owner) return;
  const audio = currentAudio;
  const onStop = currentOnStop;
  forget();
  try {
    audio.pause();
    audio.currentTime = 0;
  } catch {
    // A detached or half-loaded element — nothing left to stop.
  }
  onStop?.();
}

/** True when this owner is the one currently making noise. */
export function isPlaying(owner: unknown): boolean {
  return currentAudio !== null && currentOwner === owner;
}

/**
 * Play `url`, stopping anything else first. Resolves true when sound is
 * actually coming out, false when the browser refused (blocked autoplay, a
 * dead URL, no Audio at all) — it never throws and never logs.
 *
 * `onStop` fires exactly once when the clip ends, errors, or is stopped by
 * someone else starting theirs. It does NOT fire for a `false` result.
 */
export async function playExclusive(
  url: string,
  options: { owner?: unknown; rate?: number; onStop?: () => void } = {},
): Promise<boolean> {
  stopPlayback();
  if (typeof Audio === "undefined" || !url) return false;

  let audio: HTMLAudioElement;
  try {
    audio = new Audio(url);
  } catch {
    return false;
  }

  const settle = () => {
    if (currentAudio !== audio) return; // already superseded/stopped
    const onStop = currentOnStop;
    forget();
    onStop?.();
  };
  audio.addEventListener("ended", settle);
  audio.addEventListener("error", settle);

  currentAudio = audio;
  currentOwner = options.owner ?? null;
  currentOnStop = options.onStop ?? null;
  audio.playbackRate = options.rate ?? 1;

  try {
    await audio.play();
    return true;
  } catch {
    // Autoplay blocked, or the file never loaded: silent, deliberate no-op.
    if (currentAudio === audio) forget();
    return false;
  }
}
