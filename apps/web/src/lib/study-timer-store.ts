"use client";

import { parseStored, storageKey, type TimerState } from "./study-timer";

/**
 * localStorage as an external store for the daily timer.
 *
 * `useSyncExternalStore` is the right shape here: the server has no stored
 * progress, the client does, and React reconciles the two without a hydration
 * mismatch or a setState-in-effect cascade. Writes notify subscribers, so two
 * open tabs stay on the same count.
 */

const listeners = new Set<() => void>();

// useSyncExternalStore compares snapshots by identity, so the parsed value must
// be cached until the underlying raw string actually changes.
let cache: { key: string; raw: string | null; value: TimerState | null } = {
  key: "",
  raw: null,
  value: null,
};

function notify(): void {
  for (const listener of listeners) listener();
}

export function subscribe(onChange: () => void): () => void {
  listeners.add(onChange);
  // `storage` only fires for OTHER tabs; our own writes call notify directly.
  window.addEventListener("storage", notify);
  return () => {
    listeners.delete(onChange);
    window.removeEventListener("storage", notify);
  };
}

export function getSnapshot(userId: string): TimerState | null {
  const key = storageKey(userId);
  const raw = window.localStorage.getItem(key);
  if (cache.key === key && cache.raw === raw) return cache.value;
  cache = { key, raw, value: parseStored(raw) };
  return cache.value;
}

/** No progress exists during SSR — the client snapshot fills it in on mount. */
export function getServerSnapshot(): TimerState | null {
  return null;
}

export function write(userId: string, state: TimerState): void {
  window.localStorage.setItem(storageKey(userId), JSON.stringify(state));
  notify();
}
