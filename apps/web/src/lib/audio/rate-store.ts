"use client";

import { useSyncExternalStore } from "react";
import { parseSlowPreference, SLOW_KEY, storedSlowPreference } from "./rate";

/**
 * The app-wide "always play slowly" preference, in localStorage.
 *
 * Same shape as the daily timer's store: localStorage IS the state, read
 * through `useSyncExternalStore` so the server (which has no preference) and
 * the client (which does) reconcile without a hydration mismatch, and so two
 * open tabs agree. Default OFF — see `parseSlowPreference`.
 */

const listeners = new Set<() => void>();

// Snapshots are compared by identity, so the parsed value has to stay stable
// until the raw string actually changes.
let cache: { raw: string | null; value: boolean } = { raw: null, value: false };

/** Fallback for browsers where localStorage throws (private mode, blocked). */
let memory: boolean | null = null;

function notify(): void {
  for (const listener of listeners) listener();
}

function subscribe(onChange: () => void): () => void {
  listeners.add(onChange);
  // `storage` only fires for OTHER tabs; our own writes call notify directly.
  window.addEventListener("storage", notify);
  return () => {
    listeners.delete(onChange);
    window.removeEventListener("storage", notify);
  };
}

function getSnapshot(): boolean {
  let raw: string | null = null;
  try {
    raw = window.localStorage.getItem(SLOW_KEY);
  } catch {
    // Private mode / storage disabled: the toggle still works for this
    // session, it just won't survive a reload.
    return memory ?? false;
  }
  if (cache.raw !== raw) cache = { raw, value: parseSlowPreference(raw) };
  return cache.value;
}

/** No preference exists during SSR; the client snapshot fills it in on mount. */
function getServerSnapshot(): boolean {
  return false;
}

/** Flip the preference. Persisted, so it holds across reloads and sessions. */
export function setSlowAudio(on: boolean): void {
  try {
    window.localStorage.setItem(SLOW_KEY, storedSlowPreference(on));
  } catch {
    memory = on;
  }
  notify();
}

/** True when every play control should run at the slow rate. */
export function useSlowAudio(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
