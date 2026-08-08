"""Split a mixed-language buddy reply into per-language spans.

Mwarimu writes English with Kinyarwanda quoted inside:

    Today you learned greetings! For example, 'Mwaramutse' means 'Good
    morning!' and 'Mwiriwe' means 'Good afternoon.'

Speaking that whole string with an English voice mangles the Kinyarwanda —
unacceptable in a product whose job is pronunciation. So the reply is cut into
spans, each tagged with the voice that should say it, and the voice service
stitches them back into one clip (services/voice/tts_app.py, POST /tts/mixed).

This module is PURE: no I/O, no clock, no randomness. Same input -> same spans,
forever. It is the piece that must never regress, so the rules are deliberately
small and boring:

1. Text inside quotes (straight, curly, or guillemets) is Kinyarwanda when its
   normalized form matches a curriculum `items.sentence` the buddy was actually
   shown this connection, OR when it contains a Kinyarwanda marker word.
   A quoted English gloss ('Good morning!') matches neither and stays English.
2. Outside quotes, a marker word is Kinyarwanda on its own — that catches the
   unquoted greetings the buddy sprinkles in ("Muraho, my friend!").
3. Everything else is English.
4. Adjacent same-language spans are merged; spans with nothing pronounceable
   left in them (a lone quote mark, a dash) are dropped.

Word-level marker detection is deliberate rather than clause-level: a stray
marker inside an English clause costs one extra voice switch, whereas
clause-level guessing would hand whole English sentences to the Kinyarwanda
voice, which is the failure the caller is paying to avoid.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass

RW = "rw"
EN = "en"


@dataclass(frozen=True)
class Segment:
    text: str
    lang: str  # RW | EN

    def as_dict(self) -> dict:
        return {"text": self.text, "lang": self.lang}


# Words that mark a span as Kinyarwanda even without curriculum backing:
# greetings, courtesy and the yes/no/encouragement vocabulary the buddy uses in
# its own voice. Kept small on purpose — every entry is a word that cannot be
# mistaken for English.
MARKERS = frozenset(
    {
        "muraho", "mwaramutse", "mwiriwe", "muramuke", "murabeho", "bite",
        "amakuru", "meza", "murakoze", "urakoze", "mbabarira",
        "yego", "oya", "buhoro", "neza", "sawa", "byiza", "cyane",
        "umwana", "abana", "twige", "komera", "ndagaruka", "turabikora",
    }
)

# Opening quote -> the character that closes it. Straight quotes close
# themselves; curly ones and guillemets come in pairs.
_QUOTES: dict[str, str] = {
    '"': '"',
    "'": "'",
    "“": "”",  # “ ”
    "‘": "’",  # ‘ ’
    "«": "»",  # « »
}
# Closers that are also apostrophes (Kinyarwanda is full of cy'inyanya,
# n'amakuru): only count them as quotes at a word boundary.
_APOSTROPHE_LIKE = {"'", "’"}

_WORD_CHARS = re.compile(r"[^\w\s]", re.UNICODE)
_TOKEN = re.compile(r"\S+")
_ALNUM = re.compile(r"\w", re.UNICODE)

MAX_QUOTE_CHARS = 300  # a runaway opening quote must not swallow the reply


def normalize(text: str) -> str:
    """Lowercase, punctuation stripped, whitespace collapsed — the form both
    curriculum sentences and quoted spans are compared in."""
    return " ".join(_WORD_CHARS.sub(" ", text.lower()).split())


def _norm_word(token: str) -> str:
    return _WORD_CHARS.sub("", token.lower())


def _has_marker(text: str) -> bool:
    return any(_norm_word(t) in MARKERS for t in _TOKEN.findall(text))


def _speakable(text: str) -> bool:
    return bool(_ALNUM.search(text))


def _opens_here(text: str, i: int) -> bool:
    """A quote character opens a span only at a word boundary — otherwise the
    apostrophe in `cy'inyanya` would open a quote that never closes."""
    return i == 0 or not text[i - 1].isalnum()


def _find_close(text: str, start: int, closer: str) -> int | None:
    limit = min(len(text), start + MAX_QUOTE_CHARS)
    j = start
    while True:
        j = text.find(closer, j, limit)
        if j < 0:
            return None
        if closer not in _APOSTROPHE_LIKE or j + 1 >= len(text) or not text[j + 1].isalnum():
            return j
        j += 1  # an in-word apostrophe, keep looking


def _split_quotes(text: str) -> list[tuple[str, bool]]:
    """(chunk, was_quoted) in reading order; quote marks themselves stay with
    the surrounding chunk, where they are dropped as unpronounceable."""
    chunks: list[tuple[str, bool]] = []
    buf: list[str] = []
    i = 0
    while i < len(text):
        closer = _QUOTES.get(text[i])
        if closer is not None and _opens_here(text, i):
            j = _find_close(text, i + 1, closer)
            if j is not None and text[i + 1 : j].strip():
                chunks.append(("".join(buf), False))
                buf = []
                chunks.append((text[i + 1 : j], True))
                i = j + 1
                continue
        buf.append(text[i])
        i += 1
    chunks.append(("".join(buf), False))
    return [(c, q) for c, q in chunks if c.strip()]


def _tag_unquoted(chunk: str) -> list[Segment]:
    """Marker words become their own Kinyarwanda spans; the rest is English."""
    out: list[Segment] = []
    for token in _TOKEN.findall(chunk):
        lang = RW if _norm_word(token) in MARKERS else EN
        if out and out[-1].lang == lang:
            out[-1] = Segment(f"{out[-1].text} {token}", lang)
        else:
            out.append(Segment(token, lang))
    return out


def _merge(segments: Iterable[Segment]) -> list[Segment]:
    out: list[Segment] = []
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        if out and out[-1].lang == seg.lang:
            out[-1] = Segment(f"{out[-1].text} {text}", seg.lang)
        else:
            out.append(Segment(text, seg.lang))
    return out


def segment_reply(text: str, known_sentences: Iterable[str] = ()) -> list[Segment]:
    """Spans of `text` tagged rw/en, in order. Pure and total.

    `known_sentences` are curriculum `items.sentence` values the buddy has seen
    from a tool result this connection — a quoted span matching one of them is
    Kinyarwanda no matter what it looks like.
    """
    if not isinstance(text, str) or not text.strip():
        return []
    known = {normalize(s) for s in known_sentences if isinstance(s, str) and s.strip()}

    raw: list[Segment] = []
    for chunk, quoted in _split_quotes(text):
        if not quoted:
            raw.extend(_tag_unquoted(chunk))
        elif normalize(chunk) in known:
            raw.append(Segment(chunk.strip(), RW))
        elif any(q for _c, q in _split_quotes(chunk)):
            # Quotes inside quotes ("she said “Mwiriwe” back") — the outer pair
            # is just reported speech, so look inside it rather than handing a
            # whole English clause to the Kinyarwanda voice. Terminates: each
            # level strips at least one quote pair.
            raw.extend(segment_reply(chunk, known))
        else:
            raw.append(Segment(chunk.strip(), RW if _has_marker(chunk) else EN))

    # Merge, then drop the spans left holding only punctuation (the quote marks
    # themselves), then merge again — dropping one can join its neighbours.
    merged = _merge(raw)
    return _merge(s for s in merged if _speakable(s.text))


def segments_payload(segments: Iterable[Segment]) -> list[dict]:
    """Wire form for the voice service and the TTS cache key."""
    return [s.as_dict() for s in segments]


def mixed_key_text(payload: Iterable[dict]) -> str:
    """Canonical serialization of a span list — the body of the TTS cache key.

    Keyed on the FULL span list (text AND language), so re-saying a reply is
    free while a reply that differs only in which voice says what is not
    mistaken for it.
    """
    return json.dumps(
        [
            {"text": str(s.get("text") or ""), "lang": str(s.get("lang") or "")}
            for s in payload
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )
