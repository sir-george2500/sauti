"""Kinyarwanda spelling -> English-intuitive pronunciation respelling.

The problem this solves is the first wall an English speaker hits: Kinyarwanda
orthography is not read the way English orthography is read. `Ikinyarwanda` is
said *ee-chee-nyah-RWAHN-dah* (the `ki` is a "chi"), `cyane` is *CHAH-neh*,
`umujyi` is *oo-MOO-jee*. A learner who sounds out the letters gets it wrong
every single time, and nothing in the app tells them so.

So: `respell("Mwaramutse!") -> "mwah-rah-MOOT-seh!"` — hyphen-separated
syllables, English spelling conventions, the prominent syllable in CAPITALS.

This module is PURE: no I/O, no DB, no clock, no randomness. Same input ->
same output, forever. It is called at serialization time on data already in
memory (see services/roadmap.py, services/vocab.py), so it must stay cheap.

--------------------------------------------------------------------------
THE RULES, AND HOW SURE WE ARE OF THEM
--------------------------------------------------------------------------

Syllables. Kinyarwanda is strongly CV: every syllable is (consonant cluster +)
vowel, and there are no codas. `syllabify()` here is the single source of truth
— seed/data_kin.py imports it to build every item's `phoneme_ref`, so the
respelling and the stored syllable data can never drift apart.

Consonants that surprise an English reader:
  c, cy   -> "ch"     `cyane` CHAH-neh, `icumi` ee-CHOO-mee, `icyayi` ee-CHAH-yee
  k + i   -> "chi"    /k/ affricates before the front high vowel: `iki` EE-chee,
                      `Ikinyarwanda` ee-chee-nya-RWAHN-dah. This is the rule the
                      owner asked for and it is well attested.
  k + e   -> "che"    the same process before /e/, but WEAKER and more variable
                      speaker to speaker (see NEEDS_NATIVE_REVIEW).
  jy      -> "j"      `umujyi` oo-MOO-jee, `kujya` koo-JAH
  shy     -> "sh"     `ibishyimbo` ee-bee-SHEEM-boh
  ny      -> "ny"     one palatal nasal, as in "canyon" — NOT n + y
  ry, by, my  keep the glide (`ibiryo` ee-BEE-ryoh); before /i/ the glide is
                      redundant and dropped (`ryiza` REE-zah, `byiza` BEE-zah)
  r       -> "r"      but it is a TAP, near the "tt" of American "butter" —
                      spelling cannot carry this, the audio has to.
  g       -> "g"      hard, though intervocalically it is softer than English g.

Vowels are the plain five, spelled the way an English reader expects:
  a ah · e eh · i ee · o oh · u oo
A doubled vowel is ONE long syllable, never two: `saa` -> "saah".

Prenasalised onsets (mb nd ng nk mp nz nsh nt njy …) are single segments in
Kinyarwanda, but an English reader cannot start a syllable with "nd". When
such a syllable has something before it in the same word, the nasal is written
as a coda of that previous syllable — `rwa`+`nda` -> "rwahn-dah" — which is
what the English reader will produce anyway, and matches how the owner himself
wrote the target ("nyar-WAHN-dah"). The affricate `ts` is split the same way:
`mu`+`tse` -> "moot-seh". Word-initially there is nowhere to move it, so
`ndashaka` stays "ndah-SHAH-kah".

CAPITALS = where the pitch goes up. Kinyarwanda has lexical TONE, not English
stress, and our seed tones are editorial rather than elicited from a native
speaker. Precedence, most to least trustworthy:

  1. OVERRIDES — an exact word we have checked by hand.
  2. `phoneme_ref` syllables marked "H".  ("R" is the seed's question-rise
     mark, a phrase-final intonation contour, not word prominence — it is
     deliberately NOT capitalised.)
  3. Penultimate syllable. Not a claim that Kinyarwanda has penultimate
     stress — it does not, in the way Swahili does — but it is where the
     seeded H marks land in nearly every case, and it reproduces all six of
     the owner's hand-written targets. Monosyllables get no capital.

Read NEEDS_NATIVE_REVIEW at the bottom before trusting any of this too far.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Syllabification — shared with seed/data_kin.py, which builds phoneme_ref
# ---------------------------------------------------------------------------

# Kinyarwanda syllables are open CV: greedily take the consonant cluster plus
# its vowel(s). The trailing alternative catches apostrophe fragments (the "n"
# of `n'ibirayi`) and stray consonants.
_SYL = re.compile(r"[^aeiouAEIOU\W]*[aeiouAEIOU]+|[^aeiouAEIOU\W]+", re.UNICODE)
_CLAUSE_BREAK = re.compile(r"[,.!?…]")
_QUOTES = "'’\"“”"
_VOWELS_RE = re.compile(r"[aeiou]+")


def word_parts(word: str) -> list[str]:
    """A whitespace token split at its apostrophes, outer quotes removed.

    `rw'ibiryo` -> ["rw", "ibiryo"]: the clitic and its host are syllabified
    independently, exactly as the seed does it.
    """
    word = word.strip(_QUOTES)
    return [p for p in word.replace("’", "'").split("'") if p]


def syllabify_word(word: str) -> list[str]:
    """CV chunks of one word, lowercased."""
    return [c.lower() for part in word_parts(word) for c in _SYL.findall(part)]


def syllabify(phrase: str) -> list[str]:
    """CV chunks of a phrase's HEAD — up to the first clause break.

    The head is what the pronunciation screen drills, and it is the span
    `phoneme_ref` covers; see seed/data_kin.syl().
    """
    head = _CLAUSE_BREAK.split(phrase)[0]
    return [s for w in head.split() for s in syllabify_word(w)]


# ---------------------------------------------------------------------------
# Sound tables
# ---------------------------------------------------------------------------

SHORT_VOWELS = {"a": "ah", "e": "eh", "i": "ee", "o": "oh", "u": "oo"}
# Doubled in the orthography = phonemically long = still one syllable.
LONG_VOWELS = {"a": "aah", "e": "ehh", "i": "eee", "o": "ohh", "u": "ooh"}

# Onset cluster -> English respelling. Exhaustive over the seeded corpus plus
# the clusters Kinyarwanda allows that the corpus happens not to use.
ONSETS: dict[str, str] = {
    "": "",
    "b": "b", "bw": "bw", "by": "by",
    "c": "ch", "cy": "ch",                 # both spell /tʃ/
    "d": "d", "dw": "dw", "dy": "dy",
    "f": "f", "fw": "fw",
    "g": "g", "gw": "gw",
    "h": "h", "hw": "hw",
    "j": "j", "jy": "j",                   # jy is the plain affricate
    "k": "k", "kw": "kw",
    "l": "l",                              # loanwords only (ikilo, Kigali)
    "m": "m", "mw": "mw", "my": "my",
    "n": "n", "nw": "nw", "ny": "ny", "nyw": "nyw",
    "p": "p", "pf": "pf", "pw": "pw",
    "r": "r", "rw": "rw", "ry": "ry",
    "s": "s", "sh": "sh", "shw": "shw", "shy": "sh", "sw": "sw",
    "t": "t", "ts": "ts", "tw": "tw", "ty": "ty",
    "v": "v", "vw": "vw",
    "w": "w",
    "y": "y",
    "z": "z", "zw": "zw",
}

# Onsets an English reader cannot begin a syllable with: the first letter is
# written as a coda on the previous syllable of the same word instead.
CODA_TRANSFER: dict[str, str] = {
    "mb": "m", "mbw": "m", "mby": "m", "mf": "m", "mp": "m", "mv": "m",
    "nd": "n", "ndw": "n", "ndy": "n",
    "ng": "n", "ngw": "n",
    "nj": "n", "njy": "n",
    "nk": "n", "nkw": "n",
    "ns": "n", "nsh": "n", "nsw": "n",
    "nt": "n", "ntw": "n",
    "nz": "n", "nzw": "n",
    "ts": "t",
}
# ...but `ny`/`nyw` are the palatal nasal, a single segment, never split.

# Consonant + palatal glide where the glide is redundant before /i/:
# `ryiza` is [rʲiːza], which an English reader renders best as "REE-zah".
# `ny` is excluded — it is a phoneme in its own right, so `nyi` is "nyee".
GLIDE_DROPPED_BEFORE_I = frozenset({"by", "dy", "my", "py", "ry", "ty"})

FRONT_PALATALISING = frozenset({"i", "e"})  # /k/ -> [tʃ] before these


# ---------------------------------------------------------------------------
# Overrides — words the rules get wrong, checked by hand
# ---------------------------------------------------------------------------
#
# A rule engine that is 90% right teaches mistakes 10% of the time, so every
# word below is here for a stated reason. Keyed by the bare lowercased word
# (apostrophes kept, punctuation stripped).
OVERRIDES: dict[str, str] = {
    # -- Loanwords keep their source /k/: they are not nativised to [tʃ]. --
    "banki": "BAHN-kee",          # < English "bank"
    "ikilo": "ee-KEE-loh",        # < "kilo"; `l` itself is a loan phoneme
    "itike": "ee-TEE-keh",        # < English "ticket"
    "kigali": "kee-GAH-lee",      # see NEEDS_NATIVE_REVIEW — locals say chee-
    "kimironko": "kee-mee-ROHN-koh",  # Kigali suburb, same caveat as Kigali
    # -- Tone the penultimate default gets wrong (seed-confirmed). --
    "muraho": "moo-rah-HOH",      # phoneme_ref marks H on the final syllable
    # -- Words the seed marks inconsistently across items. A learner must see
    #    one spelling per word, so these are pinned rather than left to the
    #    editorial tone marks. See NEEDS_NATIVE_REVIEW. --
    "angahe": "ahn-GAH-heh",      # H on 'nga' in one item, on 'a' in another
    "bangahe": "bahn-GAH-heh",
    "ni": "nee",                  # toneless copula; one item marks it H
}


# ---------------------------------------------------------------------------
# Respelling
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WordRespelling:
    """One whitespace token: the original, and its respelling.

    `pronunciation` is None for tokens with nothing pronounceable in them (a
    lone dash, a stray quote) so the frontend can render them verbatim.
    """

    word: str
    pronunciation: str | None

    def as_dict(self) -> dict:
        return {"word": self.word, "pronunciation": self.pronunciation}


def _nucleus_sound(vowels: str) -> str:
    """Vowel run -> English vowels. A doubled vowel is long, not two syllables."""
    out: list[str] = []
    for match in re.finditer(r"(.)\1*", vowels):
        run = match.group(0)
        table = SHORT_VOWELS if len(run) == 1 else LONG_VOWELS
        out.append(table.get(run[0], run))
    return "".join(out)


def _cluster_sound(onset: str) -> str:
    """Onset cluster -> English consonants."""
    if onset in ONSETS:
        return ONSETS[onset]
    nasal = CODA_TRANSFER.get(onset)
    if nasal:
        # A prenasalised onset with nothing before it to carry the nasal
        # (`njya`, `mbyuka`): keep the nasal, map what follows it.
        return nasal + _cluster_sound(onset[len(nasal) :])
    return onset


def _onset_sound(onset: str, nucleus: str) -> str:
    """Onset cluster -> English consonants, in the context of its vowel."""
    if onset.endswith("k") and nucleus[:1] in FRONT_PALATALISING:
        # /k/ affricates before a front vowel: ki -> "chi", ke -> "che".
        return _cluster_sound(onset[:-1]) + "ch"
    if onset in GLIDE_DROPPED_BEFORE_I and nucleus[:1] == "i":
        return _cluster_sound(onset[:-1])
    return _cluster_sound(onset)


def _split_syllable(chunk: str) -> tuple[str, str]:
    """Onset cluster and vowel run: `nywa` -> ("nyw", "a"), `saa` -> ("s", "aa")."""
    m = _VOWELS_RE.search(chunk)
    if m is None:
        return chunk, ""
    return chunk[: m.start()], m.group(0)


def _merge_vowelless(
    chunks: list[str], tones: list[str]
) -> tuple[list[str], list[str]]:
    """Fold apostrophe fragments (`rw` of `rw'ibiryo`) into their neighbour.

    They are onsets, not syllables — `rw` + `i` is one syllable, "rwee". Tones
    are merged too, so an H on either part survives.
    """
    out_chunks: list[str] = []
    out_tones: list[str] = []
    pending = ""
    pending_tone = "L"
    for chunk, tone in zip(chunks, tones):
        if not _VOWELS_RE.search(chunk):
            pending += chunk
            pending_tone = tone if tone == "H" else pending_tone
            continue
        out_chunks.append(pending + chunk)
        out_tones.append("H" if "H" in (pending_tone, tone) else tone)
        pending, pending_tone = "", "L"
    if pending:  # trailing consonant with no vowel to attach to
        if out_chunks:
            out_chunks[-1] += pending
        else:
            out_chunks.append(pending)
            out_tones.append(pending_tone)
    return out_chunks, out_tones


def respell_syllables(chunks: list[str], tones: list[str] | None = None) -> str:
    """Respell one word's CV chunks. `tones` is parallel: "H" | "R" | "L"."""
    tones = list(tones or [])
    tones += ["L"] * (len(chunks) - len(tones))
    chunks, tones = _merge_vowelless(chunks, tones[: len(chunks)])
    if not chunks:
        return ""

    parts: list[str] = []
    for idx, chunk in enumerate(chunks):
        onset, nucleus = _split_syllable(chunk)
        moved = CODA_TRANSFER.get(onset)
        if moved and idx > 0:
            parts[-1] += moved
            onset = onset[len(moved) :]
        parts.append(_onset_sound(onset, nucleus) + _nucleus_sound(nucleus))

    highs = [i for i, t in enumerate(tones) if t == "H"]
    if not highs and len(parts) >= 2:
        highs = [len(parts) - 2]  # penultimate default; monosyllables stay flat
    for i in highs:
        parts[i] = parts[i].upper()
    return "-".join(p for p in parts if p)


def respell_word(word: str, tones: list[str] | None = None) -> str | None:
    """Respell a single token, punctuation preserved around it.

    None when the token holds nothing pronounceable.
    """
    if not isinstance(word, str):
        return None
    lead = 0
    while lead < len(word) and not word[lead].isalpha():
        lead += 1
    trail = len(word)
    while trail > lead and not word[trail - 1].isalpha():
        trail -= 1
    core = word[lead:trail]
    if not core:
        return None
    prefix, suffix = word[:lead], word[trail:]

    key = core.lower().replace("’", "'")
    body = OVERRIDES.get(key) or respell_syllables(syllabify_word(core), tones)
    return f"{prefix}{body}{suffix}" if body else None


def _tones_by_word(sentence: str, phoneme_ref: dict | None) -> list[list[str]]:
    """Per-word tone lists, aligned to `phoneme_ref["syllables"]`.

    `phoneme_ref` is a FLAT list built by the same syllabifier, and it covers
    only the sentence head (up to the first clause break). Alignment is by
    position and verified chunk-by-chunk: the moment a syllable string stops
    matching, tone data is abandoned for the rest of the sentence rather than
    silently capitalising the wrong syllable.
    """
    words = sentence.split()
    per_word = [syllabify_word(w) for w in words]
    stored = (phoneme_ref or {}).get("syllables") or []
    if not isinstance(stored, list):
        stored = []

    tones: list[list[str]] = []
    cursor = 0
    aligned = True
    for chunks in per_word:
        row: list[str] = []
        for chunk in chunks:
            if not aligned or cursor >= len(stored):
                # Past the head phoneme_ref covers (or past a mismatch): flat.
                row.append("L")
            else:
                entry = stored[cursor]
                if isinstance(entry, dict) and entry.get("syl") == chunk:
                    row.append(str(entry.get("tone") or "L"))
                else:
                    aligned = False
                    row.append("L")
            cursor += 1
        tones.append(row)
    return tones


def respell_words(sentence: str, phoneme_ref: dict | None = None) -> list[WordRespelling]:
    """Per-word respelling, in order — so the frontend can align word by word."""
    if not isinstance(sentence, str) or not sentence.strip():
        return []
    words = sentence.split()
    tones = _tones_by_word(sentence, phoneme_ref)
    return [
        WordRespelling(word=w, pronunciation=respell_word(w, t))
        for w, t in zip(words, tones)
    ]


def respell(sentence: str, phoneme_ref: dict | None = None) -> str | None:
    """Kinyarwanda sentence -> hyphenated English respelling, or None.

    None (rather than "") when there is nothing to say, so an item payload can
    carry `pronunciation: null` and the UI can simply not render the line.

    Token count is preserved: the result has exactly as many whitespace-
    separated tokens as `sentence`, so a client can zip the two together
    word-by-word with a plain `.split()`. A token with nothing pronounceable in
    it (a lone dash) is passed through unchanged rather than dropped.
    """
    parts = respell_words(sentence, phoneme_ref)
    if not any(p.pronunciation for p in parts):
        return None
    return " ".join(p.pronunciation or p.word for p in parts)


# ---------------------------------------------------------------------------
# Honest limits
# ---------------------------------------------------------------------------
#
# Things a Kinyarwanda speaker should look at before we claim these are right.
# Each entry is a real uncertainty, not a to-do.
NEEDS_NATIVE_REVIEW: tuple[str, ...] = (
    "TONE, everywhere. Kinyarwanda tone is lexical and our seed marks it on "
    "only 25 of 158 items — and most of those marks are the question-rise "
    "'R', not word tone. Every other word is capitalised by the penultimate "
    "default, which is a reasonable guess and nothing more.",
    "k + e ('keza', 'make'). Affrication before /e/ is weaker and more "
    "variable than before /i/; 'CHEH-zah' may overshoot to a full 'ch'.",
    "'Kigali' / 'Kimironko'. Native Kinyarwanda has [tʃi] here — 'chee-GAH-lee' "
    "— but every map, sign and English conversation says 'kee-GAH-lee'. "
    "Overridden to the international form; a native speaker should decide.",
    "g before front vowels ('igitabo', 'gikoni'). Written hard 'g'; the real "
    "sound is softer than an English g and may be palatalised.",
    "'by' ('byiza', 'ibyumba') and 'ry' ('ibiryo'). Described in the "
    "literature as affricated [bʑ] / palatalised [rʲ]; 'by'/'ry' here is an "
    "approximation and drops the glide entirely before /i/.",
    "'r' is a tap, near the 'tt' of American 'butter'. The respelling writes "
    "'r' because there is no English spelling for a tap — the audio must "
    "carry this one.",
    "'j' is written 'j'; the Kinyarwanda sound sits between the 'j' of 'jam' "
    "and the 's' of 'measure'.",
    "Long vowels that are not written double (compensatory lengthening in "
    "'icyumba', 'cyuma') are not marked — we only lengthen what the "
    "orthography doubles.",
    "'angahe' is marked H on two different syllables in two different seeded "
    "items ('Ni angahe?' vs 'Ni angahe kugera ku isoko?'). At most one can be "
    "right.",
)
