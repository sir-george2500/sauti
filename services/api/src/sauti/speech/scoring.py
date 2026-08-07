"""Deterministic pronunciation scoring — ASR transcript vs reference sentence.

No LLM, no randomness: the learner's take is transcribed (FastConformer) and
compared against the item's sentence with sequence alignment.

  overall   = 60% word-level alignment + 40% character-level similarity (0-100)
  syllables = each syllable in the item's phoneme_ref inherits the score of the
              word it belongs to (a substituted/missed word drops ALL of its
              syllables), so feedback chips point at the words that went wrong
  tone      = a phoneme_ref tone hint (H/R/F) is flagged when its syllable's
              parent word mismatched — we cannot hear pitch from a transcript,
              but a garbled word means the tone contour was certainly lost

Pure functions, unit-tested hard in tests/unit/test_pron_scoring.py.
"""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from sauti.schemas.common import PhonemeScore, PronReport

WORD_WEIGHT = 0.6
CHAR_WEIGHT = 0.4
SYL_OK = 70  # under this a syllable earns a note; tone hints there get flagged

_PUNCT = re.compile(r"[^\w\s']", re.UNICODE)
_WS = re.compile(r"\s+")


def normalize(text: str) -> str:
    """NFC, lowercase, punctuation stripped, whitespace collapsed."""
    text = unicodedata.normalize("NFC", text).lower().replace("’", "'")
    text = _PUNCT.sub(" ", text)
    return _WS.sub(" ", text).strip()


def _ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _word_results(ref_words: list[str], hyp_words: list[str]) -> list[tuple[float, str | None]]:
    """Per reference word: (score 0..100, closest heard word or None if missing).

    difflib alignment on the word sequences; words inside a `replace` block are
    scored by their best character-level match in the opposing block, `delete`d
    words score 0.
    """
    results: list[tuple[float, str | None]] = [(0.0, None)] * len(ref_words)
    sm = SequenceMatcher(None, ref_words, hyp_words)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for i in range(i1, i2):
                results[i] = (100.0, ref_words[i])
        elif tag == "replace":
            block = hyp_words[j1:j2]
            for i in range(i1, i2):
                best = max(block, key=lambda h: _ratio(ref_words[i], h))
                results[i] = (_ratio(ref_words[i], best) * 100.0, best)
        # "delete": ref words never heard — stay (0, None).
        # "insert": extra spoken words — penalized via the char-level term.
    return results


def _syllable_parents(ref_words: list[str], syllables: list[dict]) -> list[int]:
    """Parent word index for each syllable of the item's phoneme_ref.

    The seed builds syllables word by word (CV chunks, apostrophes dropped), so
    greedily concatenating syllables reconstructs each word in order. If the
    reconstruction diverges (hand-edited content), fall back to spreading the
    syllables proportionally across the words.
    """
    targets = [w.replace("'", "") for w in ref_words]
    parents: list[int] = []
    w, acc, ok = 0, "", True
    for s in syllables:
        name = str(s.get("syl", "") if isinstance(s, dict) else s).lower()
        if w >= len(targets):
            ok = False
            break
        acc += name
        parents.append(w)
        if acc == targets[w]:
            w, acc = w + 1, ""
        elif not targets[w].startswith(acc):
            ok = False
            break  # diverged — fall back below
    if ok and len(parents) == len(syllables):
        return parents
    n = max(len(ref_words), 1)
    return [min(i * n // max(len(syllables), 1), n - 1) for i in range(len(syllables))]


def score_pronunciation(sentence: str, transcript: str, phoneme_ref: dict) -> PronReport:
    ref_words = normalize(sentence).split()
    hyp_words = normalize(transcript).split()
    syllables = phoneme_ref.get("syllables") or []

    if not ref_words:  # defensive: unscoreable item
        return PronReport(overall=0, phonemes=[], tone_flags=[], transcript=transcript)

    word_results = _word_results(ref_words, hyp_words)
    word_level = sum(score for score, _ in word_results) / len(word_results)
    char_level = _ratio("".join(ref_words), "".join(hyp_words)) * 100.0
    overall = round(WORD_WEIGHT * word_level + CHAR_WEIGHT * char_level)
    overall = max(0, min(100, overall))

    parents = _syllable_parents(ref_words, syllables)
    phonemes: list[PhonemeScore] = []
    tone_flags: list[str] = []
    for idx, syl in enumerate(syllables):
        name = syl.get("syl", "??") if isinstance(syl, dict) else str(syl)
        tone = syl.get("tone") if isinstance(syl, dict) else None
        w = parents[idx] if idx < len(parents) else len(ref_words) - 1
        score, heard = word_results[w]
        s = max(0, min(100, round(score)))
        note = None
        if s < SYL_OK:
            if heard is None:
                note = f"'{ref_words[w]}' didn't come through — say the whole word"
            else:
                note = f"'{ref_words[w]}' sounded like '{heard}' — shape this syllable"
            if tone in ("H", "R", "F"):
                tone_flags.append(
                    f"tone on '{name}' was lost — aim for a "
                    f"{'rise' if tone in ('H', 'R') else 'fall'}"
                )
        phonemes.append(PhonemeScore(phoneme=name, score=s, note=note))

    return PronReport(
        overall=overall, phonemes=phonemes, tone_flags=tone_flags, transcript=transcript
    )
