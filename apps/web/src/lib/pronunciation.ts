/**
 * English respelling of a Kinyarwanda line — `Mwaramutse` → `mwah-rah-MOOT-seh`.
 *
 * The backend ships it as `item.pronunciation` (roadmap lesson items and
 * `/vocab/decks/{tag}`), stressed syllable in CAPS, hyphen between syllables.
 * The field is optional and often null, so everything here is written to fold
 * back to "render the Kinyarwanda alone" without a placeholder.
 *
 * Pairing is word-by-word so each respelling sits over the word it belongs to
 * (that is the whole point for a reader who can't yet map spelling to sound),
 * and so a long line still wraps at the spaces instead of running off the card.
 */

export interface RespellPair {
  /** One Kinyarwanda word, exactly as written — punctuation included. */
  base: string;
  /** Its respelling. */
  guide: string;
}

export interface Syllable {
  text: string;
  /** ALL-CAPS in the respelling means "this is the stressed syllable". */
  stressed: boolean;
}

/**
 * Split a sentence and its guide into aligned word/respelling pairs.
 *
 * `null` means there is nothing to annotate (no guide, or nothing to put it
 * over) — callers render the plain sentence and add no markup at all.
 */
export function respellPairs(
  sentence: string,
  guide?: string | null,
): RespellPair[] | null {
  const text = (sentence ?? "").trim();
  const annotation = (guide ?? "").trim();
  if (!text || !annotation) return null;

  const words = text.split(/\s+/);
  const guides = annotation.split(/\s+/);
  if (words.length === guides.length) {
    return words.map((base, i) => ({ base, guide: guides[i] }));
  }
  // The counts disagree — a guide written for a different tokenisation, or a
  // partial one. Annotating the whole phrase once is honest; guessing which
  // word each fragment belongs to would put the wrong sound over the wrong
  // syllable, which is worse than no guide at all.
  return [{ base: text, guide: annotation }];
}

/** A guide's syllables, flagging the capitalised (stressed) one. */
export function syllables(guide: string): Syllable[] {
  return guide.split("-").map((text) => ({ text, stressed: isStressed(text) }));
}

/** CAPS carries the stress — but only when there is a letter to capitalise. */
function isStressed(syllable: string): boolean {
  return /\p{Lu}/u.test(syllable) && syllable === syllable.toUpperCase();
}
