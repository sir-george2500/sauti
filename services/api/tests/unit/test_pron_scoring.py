"""Pronunciation scoring — deterministic alignment scoring, tested hard.

The scorer never sees audio: it compares the ASR transcript against the item's
sentence. These tests pin the contract the pronunciation screen relies on.
"""
from __future__ import annotations

from sauti.speech.scoring import normalize, score_pronunciation


def syls(*chunks: str, tones: dict[int, str] | None = None) -> dict:
    out = [{"syl": c, "tone": "L"} for c in chunks]
    for i, t in (tones or {}).items():
        out[i]["tone"] = t
    return {"syllables": out}


MWARAMUTSE = syls("mwa", "ra", "mu", "tse")
NI_MEZA_URAKOZE = syls("ni", "me", "za", "u", "ra", "ko", "ze")


class TestNormalize:
    def test_case_punctuation_whitespace(self):
        assert normalize("  Mwaramutse!  ") == "mwaramutse"
        assert normalize("Ni meza, urakoze.") == "ni meza urakoze"

    def test_apostrophes_kept_curly_folded(self):
        assert normalize("n’ejo") == "n'ejo"


class TestOverall:
    def test_perfect_match_scores_95_plus(self):
        r = score_pronunciation("Mwaramutse!", "mwaramutse", MWARAMUTSE)
        assert r.overall >= 95
        assert all(p.score >= 95 for p in r.phonemes)
        assert r.tone_flags == []

    def test_case_and_punctuation_do_not_matter(self):
        a = score_pronunciation("Ni meza, urakoze.", "ni meza urakoze", NI_MEZA_URAKOZE)
        b = score_pronunciation("Ni meza, urakoze.", "NI MEZA, URAKOZE!", NI_MEZA_URAKOZE)
        assert a.overall == b.overall >= 95

    def test_gibberish_scores_low(self):
        r = score_pronunciation("Mwaramutse!", "zzz bbb qqq", MWARAMUTSE)
        assert r.overall <= 30
        assert all(p.score <= 30 for p in r.phonemes)

    def test_empty_transcript_scores_zero(self):
        r = score_pronunciation("Mwaramutse!", "", MWARAMUTSE)
        assert r.overall == 0
        assert all(p.score == 0 for p in r.phonemes)
        assert all(p.note for p in r.phonemes)

    def test_transcript_travels_in_the_report(self):
        r = score_pronunciation("Mwaramutse!", "mwaramutse", MWARAMUTSE)
        assert r.transcript == "mwaramutse"

    def test_near_match_beats_wrong_word(self):
        near = score_pronunciation("Urakoze cyane.", "urakoze cyana", syls("u", "ra", "ko", "ze", "cya", "ne"))
        wrong = score_pronunciation("Urakoze cyane.", "urakoze amata", syls("u", "ra", "ko", "ze", "cya", "ne"))
        assert near.overall > wrong.overall


class TestSyllableAttribution:
    def test_wrong_word_drops_only_its_syllables(self):
        # "urakoze" replaced by something unrelated; "ni meza" said fine.
        r = score_pronunciation("Ni meza, urakoze.", "ni meza amata", NI_MEZA_URAKOZE)
        by_name = {}
        for p in r.phonemes:
            by_name.setdefault(p.phoneme, p)
        assert by_name["ni"].score == 100
        assert by_name["me"].score == 100
        assert by_name["za"].score == 100
        # every syllable of the substituted word drops below the OK bar
        for p in r.phonemes[3:]:
            assert p.score < 70
            assert p.note is not None and "urakoze" in p.note

    def test_missing_word_notes_it_was_not_heard(self):
        r = score_pronunciation("Ni meza, urakoze.", "ni meza", NI_MEZA_URAKOZE)
        tail = r.phonemes[3:]
        assert all(p.score == 0 for p in tail)
        assert all("didn't come through" in (p.note or "") for p in tail)

    def test_apostrophe_words_map_cleanly(self):
        ref = syls("tu", "za", "bo", "na", "na", "n", "e", "jo")
        r = score_pronunciation("Tuzabonana n'ejo.", "tuzabonana", ref)
        assert [p.score for p in r.phonemes[:5]] == [100] * 5
        assert all(p.score == 0 for p in r.phonemes[5:])

    def test_unreconstructable_syllables_still_scored(self):
        # Hand-edited phoneme_ref that no longer concatenates into the words —
        # proportional fallback keeps one score per syllable.
        r = score_pronunciation("Ni meza.", "ni meza", syls("xx", "yy"))
        assert len(r.phonemes) == 2
        assert all(0 <= p.score <= 100 for p in r.phonemes)


class TestToneFlags:
    def test_tone_flag_surfaces_when_its_syllable_mismatches(self):
        ref = syls("mu", "ra", "ho", tones={2: "H"})
        r = score_pronunciation("Muraho!", "amakuru", ref)
        assert any("'ho'" in f for f in r.tone_flags)
        assert any("rise" in f for f in r.tone_flags)

    def test_no_tone_flag_when_word_matches(self):
        ref = syls("mu", "ra", "ho", tones={2: "H"})
        r = score_pronunciation("Muraho!", "muraho", ref)
        assert r.tone_flags == []

    def test_fall_wording_for_f_tone(self):
        ref = syls("mu", "ra", "ho", tones={1: "F"})
        r = score_pronunciation("Muraho!", "ikawa", ref)
        assert any("fall" in f for f in r.tone_flags)


class TestDeterminism:
    def test_same_inputs_same_report(self):
        a = score_pronunciation("Amakuru yawe?", "amakuru yacu", syls("a", "ma", "ku", "ru", "ya", "we"))
        b = score_pronunciation("Amakuru yawe?", "amakuru yacu", syls("a", "ma", "ku", "ru", "ya", "we"))
        assert a.model_dump() == b.model_dump()
