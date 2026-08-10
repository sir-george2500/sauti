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

The palatal series is where an English reader goes wrong, and it is NOT the
"ch" everyone reaches for. Kinyarwanda distinguishes a palatal STOP [c] from
the affricate [tʃ], and spells them differently:

  c       -> "ch"    the affricate [tʃ], "ch as in church" (Cox & Gakuba):
                     `icumi` ee-CHOO-mee, `umuceri` oo-moo-CHEH-ree
  cy      -> "ky"    the palatal STOP [c], a different sound: `cyane` KYAH-neh,
                     `icyumba` ee-KYOOM-bah. English ears hear [c] as "ch" —
                     that mishearing is where the folk "ichinyarwanda" comes
                     from — but producing an English "ch" here merges a real
                     contrast (c vs cy both occur before all five vowels:
                     gucika/cyiza, amacumu/icyumba). "ky" as in "cute" is the
                     nearest English sequence; [kj] is an attested variant of
                     this series.
  jy      -> "gy"    [ɟ], the voiced partner of cy: `umujyi` oo-MOO-gyee
  k + i/e -> "ky"    /k/ palatalises before a front vowel, everywhere in the
  g + i/e -> "gy"    word including finally (`ibitoki`, `urutoki`). Meeussen
                     (1959:10) via Kochetov (2016) gives [kji~ci] / [ɡji~ɟi];
                     Wikipedia's orthography section calls it speaker's
                     preference, i.e. OPTIONAL. We write the [kj]/[ɡj] variant
                     because it is attested, is what the owner is hearing, and
                     is recoverable — "chee" would not be.
  shy     -> "sh"    really [ç] (German "ich"); "sh" is the usable English near
  ny      -> "ny"    [ɲ], one segment, as in "canyon" — NOT n + y
  by, ry, my         keep the glide letter: by is [bɟ] and ry is [ɾɟ] ("a
                     slight g sound between the r and y, but not very strong"
                     — Cox & Gakuba), so "by"/"ry" [bj]/[ɾj] is the near miss,
                     and "bj" would be the wrong one.
  r       -> "r"     a TAP, near the "tt" of American "butter". No English
                     spelling carries this; the audio has to.
  b       -> "b"     but between vowels it lenites to [β], a b made with both
                     lips and softer than an English b (`umugabo` is closer to
                     "oo-moo-GAH-vo"). Writing "v" would overshoot into a
                     labiodental, so this one is left to the audio too.

Vowels are the plain five, spelled the way an English reader expects:
  a ah · e eh · i ee · o oh · u oo

Vowel LENGTH is phonemic in Kinyarwanda and is deliberately NOT rendered here.
Rwandan orthography does not write it (the 1985 orthographic law prohibits
doubled vowels; a corpus check of Webonary finds zero doubled-vowel headwords),
so it would have to be derived — short word-initially and word-finally, fully
long after a palatalised or labio-velarised consonant, intermediate before a
prenasalised cluster (Kimenyi; Myers 2005, J. Phonetics 33:427-446). We can
derive it, but we cannot SPELL it: `byiza` would come out "byeee-zah" and
`kwishyura` "kweee-SHOOH-rah", which is less usable than saying nothing and
letting the audio carry it. Where the orthography does happen to write a double
(`saa`), it stays one long syllable — never two.

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
  3. Penultimate syllable. Kinyarwanda has no phonological penultimate stress
     the way Swahili and Zulu do, but it does show gradient phonetic
     penultimate lengthening (Myers 2005 via Hyman 2009; Hamlaoui, Engelmann &
     Szendrői 2022). So this is a light default, not a claim — and it never
     overrides a marked lexical H. Monosyllables get no capital.

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
# Rwandan orthography does not write long vowels at all, so this table only
# fires on the handful of spellings that do carry a double (`saa`) — never on
# derived length, which we decline to render. Still ONE syllable either way.
LONG_VOWELS = {"a": "aah", "e": "ehh", "i": "eee", "o": "ohh", "u": "ooh"}

# Onset cluster -> English respelling. Exhaustive over the seeded corpus plus
# the clusters Kinyarwanda allows that the corpus happens not to use.
ONSETS: dict[str, str] = {
    "": "",
    "b": "b", "bw": "bw", "by": "by",
    "c": "ch",                             # the affricate [tʃ], as in "church"
    "cy": "ky",                            # the palatal STOP [c] — NOT the same
    "d": "d", "dw": "dw", "dy": "dy",
    "f": "f", "fw": "fw",
    "g": "g", "gw": "gw",
    "h": "h", "hw": "hw",
    "j": "j",                              # [ʒ]~[dʒ]
    "jy": "gy",                            # [ɟ], the voiced palatal stop
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

# A velar before a front vowel is palatalised: /ki ke/ -> [kji~ci] and
# /gi ge/ -> [ɡji~ɟi] (Meeussen 1959:10, via Kochetov 2016). Purely
# phonological — it fires wherever the front vowel is, including word-finally
# (`urutoki`, `ibitoki`), not only after a class prefix.
FRONT_PALATALISING = frozenset({"i", "e"})
PALATALISED_VELAR = {"k": "ky", "g": "gy"}

# The Kinyarwanda alphabet. No q, no x, nothing accented. A word using a letter
# outside it is not Kinyarwanda, so we decline to respell it rather than
# inventing a pronunciation (see `respell_word`).
ALPHABET = frozenset("abcdefghijklmnoprstuvwyz")

# These rules are Kinyarwanda rules and nothing else. Swahili spells `ki` as a
# plain "kee" (kitabu), French shares almost nothing with any of this — running
# the engine over either produces confident nonsense, so callers name the
# course and only KIN gets respelled.
RESPELLED_COURSE_CODES = frozenset({"KIN"})


# ---------------------------------------------------------------------------
# Overrides — words the rules get wrong, checked by hand
# ---------------------------------------------------------------------------
#
# A rule engine that is 90% right teaches mistakes 10% of the time, so every
# word below is here for a stated reason. Keyed by the bare lowercased word
# (apostrophes kept, punctuation stripped).
OVERRIDES: dict[str, str] = {
    # -- Loans that were NOT reanalysed into a Kinyarwanda noun class stay
    #    outside the palatalisation domain and keep a plain [k]. The Rwandan-
    #    authored Iriza dictionary transcribes `banki` [baanki], one of very
    #    few unpalatalised bracketings in the book. `itike` is the same shape.
    #    Loans that WERE reanalysed (ikilo/ikiro, igitabo < Sw. kitabu) do
    #    palatalise and are deliberately NOT listed here. --
    "banki": "BAHN-kee",          # < English "bank", class 9
    "itike": "ee-TEE-keh",        # < English "ticket", class 9
    # -- Place names kept in the form every map, sign and English conversation
    #    uses. Note this is a choice, not a finding: Kigali is morphologically
    #    class-7 ki- + -gali, and Iriza transcribes it /kyi-ga-li/. Top of the
    #    review list. --
    "kigali": "kee-GAH-lee",
    "kimironko": "kee-mee-ROHN-koh",
    # -- A French given name in a Kinyarwanda sentence; the velar rule would
    #    turn it into "AHN-gyeh". --
    "ange": "AHN-jeh",
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
    palatalised = PALATALISED_VELAR.get(onset[-1:])
    if palatalised and nucleus[:1] in FRONT_PALATALISING:
        return _cluster_sound(onset[:-1]) + palatalised
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
    if not core or not set(core.lower()) <= ALPHABET | {"'", "’"}:
        # Not spellable in Kinyarwanda (ç, é, q, x): say nothing rather than
        # guess. The caller passes the token through unchanged.
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
    "TONE, everywhere, and it is the weakest thing here. Kinyarwanda tone is "
    "lexical H vs nothing, borne by the mora, and our seed marks it on only 25 "
    "of 158 items — most of those being the question-rise 'R', not word tone. "
    "Everything else is capitalised by the penultimate default, which rests on "
    "gradient phonetic penultimate LENGTHENING (Myers 2005), not on stress: "
    "Kinyarwanda has no phonological penultimate stress, and Kimenyi's "
    "reference sketch never mentions stress at all.",
    "'amakuru' — we capitalise the penult ('ah-mah-KOO-roo'), following the "
    "seed's H mark and the owner's own hand-written target, but Wiktionary "
    "gives 'amakurú' with H on the FINAL syllable. Flagged rather than flipped "
    "on a single weak source.",
    "'muraho' — same shape of disagreement the other way: the seed marks H on "
    "the final ('moo-rah-HOH', which is what we ship), Wiktionary gives "
    "'muráho' with H on the penult.",
    "'angahe' is marked H on two different syllables in two different seeded "
    "items ('Ni angahe?' vs 'Ni angahe kugera ku isoko?'). At most one can be "
    "right; pinned to the penult so a learner sees one spelling.",
    "'ki'/'ke'/'gi'/'ge' -> 'ky'/'gy'. The palatalised realisation is real but "
    "OPTIONAL: Meeussen (1959:10) via Kochetov (2016) gives the range "
    "[kʲi~ci], and the northern Kirera dialect de-palatalises systematically "
    "(Dukuzumuremyi et al. 2024). No acoustic study of this alternation "
    "appears to exist. We write the [kʲ] end of the range; a speaker may "
    "prefer the plain velar, and both are correct.",
    "'cy' -> 'ky' is the correction that changes the most words, and it "
    "contradicts what an English ear reports. `cy` is the palatal STOP [c] "
    "(Kimenyi lists cy/jy/shy as palatalised velars, and writes the "
    "derivation *ikyúuma > icyuma); `c` alone is the affricate [tʃ]. Both "
    "occur before all five vowels, so they cannot be merged into one 'ch' "
    "without destroying a contrast. Kirundi HAS merged them, which is where "
    "some of the 'ch' transcriptions come from.",
    "'Kigali' / 'Kimironko' are shipped unpalatalised as a deliberate choice "
    "about place names, NOT as a finding. Kigali is morphologically class-7 "
    "ki- + -gali, and the Rwandan-authored Iriza dictionary transcribes it "
    "/kyi-ga-li/. If the owner would rather sound local than international, "
    "these two overrides should go.",
    "Loanwords: whether 'banki' and 'itike' really block palatalisation is a "
    "genuine gap. No source states a loanword exemption; the split we encode "
    "is noun-class reanalysis (ikilo, igitabo palatalise — they took class 7 "
    "and even Dahl's Law; banki, itike did not), resting on one Iriza "
    "bracketing, `banki [baanki]`.",
    "VOWEL LENGTH is phonemic and we render none of it. Rwandan orthography "
    "does not write it (1985 law) so it must be derived — short word-initially "
    "and word-finally, long after a consonant+glide, longer-but-not-long "
    "before a prenasalised cluster (Kimenyi 1979 says 'always lengthen' there; "
    "Myers 2005 measured it as intermediate and disagrees). Deriving it is "
    "easy; SPELLING it is not, and 'byeee-zah' would cost more than it buys.",
    "'mp', 'nt', 'nk' are aspirated, and Kimenyi reports 'mp' as [mh] outright "
    "(impamvu ≈ 'eem-HAAM-vu'). Only 'mpa' in this corpus is affected, and it "
    "is shipped as 'mpah'.",
    "Glide clusters STRENGTHEN to stops in a way English spelling cannot "
    "carry: by [bɟ], ry [ɾɟ], mw [mŋ] (umwana ≈ 'oo-MNGAA-nah'), tw [tkw], "
    "rw [ɾgw], bw [bg], nyw [ɲŋw], shy [ç]. We write the plain digraphs; the "
    "audio has to teach these.",
    "'r' is a tap, near the 'tt' of American 'butter' (and orthographic 'l' in "
    "loans is the same tap). There is no English spelling for it.",
    "'b' between vowels lenites to the bilabial fricative [β] — 'umugabo' is "
    "nearer 'oo-moo-GAH-vo'. Written 'b', because 'v' would overshoot into a "
    "labiodental and would then be wrong after a nasal ('imbwa').",
)
