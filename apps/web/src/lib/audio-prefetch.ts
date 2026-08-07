/**
 * Per-lesson audio prefetch (design rule: "audio prefetched per lesson").
 *
 * When a lesson/deck screen loads, warm preload='auto' Audio elements for the
 * items' direct audio_urls so the FIRST tap plays from cache instead of
 * paying the network round trip. Only direct CDN urls are warmed — the /tts
 * fallback route is auth'd + 302 and not worth speculative hits.
 *
 * Data-frugal: skipped entirely on Save-Data or 2g connections, and capped
 * per call so a long deck never soaks a metered plan.
 */

interface NetworkInformationLike {
  saveData?: boolean;
  effectiveType?: string;
}

export const PREFETCH_CAP = 15;

/** Warmed elements, by URL — the Map both dedupes and pins them against GC. */
const warmed = new Map<string, HTMLAudioElement>();

export function connectionAllowsPrefetch(
  conn: NetworkInformationLike | undefined = typeof navigator === "undefined"
    ? undefined
    : (navigator as Navigator & { connection?: NetworkInformationLike }).connection,
): boolean {
  if (!conn) return true; // API unsupported — assume a decent connection
  if (conn.saveData) return false;
  const type = conn.effectiveType ?? "";
  return type !== "2g" && type !== "slow-2g";
}

/**
 * Start background loads for up to `cap` not-yet-warmed urls.
 * Returns how many loads were started (0 on server, slow/metered networks).
 */
export function prefetchAudio(
  urls: Array<string | null | undefined>,
  cap: number = PREFETCH_CAP,
): number {
  if (typeof window === "undefined" || typeof Audio === "undefined") return 0;
  if (!connectionAllowsPrefetch()) return 0;
  let started = 0;
  for (const url of urls) {
    if (started >= cap) break;
    if (!url || warmed.has(url)) continue;
    const audio = new Audio();
    audio.preload = "auto";
    audio.src = url;
    audio.load();
    warmed.set(url, audio);
    started++;
  }
  return started;
}

/** Test hook — forget everything warmed so far. */
export function _resetPrefetchCache(): void {
  warmed.clear();
}
