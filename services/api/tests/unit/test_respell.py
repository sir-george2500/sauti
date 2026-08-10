"""Pronunciation respelling — the table the owner reads out loud.

Every row here is a claim about how Kinyarwanda is pronounced. If one of them
regresses, the app teaches a mispronunciation, which is worse than teaching
nothing, so the table is deliberately exhaustive over the seeded corpus.
"""
from __future__ import annotations

import re

import pytest

from sauti.seed.data_kin import COURSE_KIN, syl
from sauti.speech.respell import (
    NEEDS_NATIVE_REVIEW,
    OVERRIDES,
    respell,
    respell_word,
    respell_words,
    syllabify,
    syllabify_word,
)

SEEDED_ITEMS = [
    item
    for level in COURSE_KIN["levels"]
    for unit in level["units"]
    for lesson in unit["lessons"]
    for item in lesson["items"]
]


def word(w: str) -> str | None:
    """Respell one bare word with no tone data — the pure rule engine."""
    return respell_word(w)


class TestOwnersTargets:
    """The six respellings the owner wrote by hand when he asked for this."""

    @pytest.mark.parametrize(
        "sentence,expected",
        [
            ("Mwaramutse", "mwah-rah-MOOT-seh"),
            ("Amakuru", "ah-mah-KOO-roo"),
            ("Murakoze", "moo-rah-KOH-zeh"),
            ("umwana", "oo-MWAH-nah"),
            ("Buhoro", "boo-HOH-roh"),
        ],
    )
    def test_matches_exactly(self, sentence, expected):
        assert respell(sentence) == expected

    def test_ikinyarwanda_keeps_the_nasal_with_its_own_syllable(self):
        # The owner wrote "ee-chee-nyar-WAHN-dah"; `rw` is one onset [rʷ], so
        # the r belongs to the stressed syllable, not to the one before it.
        # Everything else — the ki -> "chi", the coda n, the capital — matches.
        assert respell("Ikinyarwanda") == "ee-chee-nyah-RWAHN-dah"


class TestPalatalisation:
    """The rule that started all this: spelling k/c is not sound k/c."""

    @pytest.mark.parametrize(
        "kinyarwanda,expected",
        [
            # k + i -> "chi"
            ("iki", "EE-chee"),
            ("kimwe", "CHEE-mweh"),
            ("bakinira", "bah-chee-NEE-rah"),
            ("ibitoki", "ee-bee-TOH-chee"),
            # k + e -> "che"
            ("keza", "CHEH-zah"),
            ("make", "MAH-cheh"),
            # k elsewhere stays k
            ("ikawa", "ee-KAH-wah"),
            ("komeza", "koh-MEH-zah"),
            ("kuruta", "koo-ROO-tah"),
            ("gikoni", "gee-KOH-nee"),
            # ...including before a glide, where no front vowel follows it
            ("kwishyura", "kwee-SHOO-rah"),
            # `cy` and bare `c` both spell the same "ch"
            ("cyane", "CHAH-neh"),
            ("cyiza", "CHEE-zah"),
            ("icyayi", "ee-CHAH-yee"),
            ("icyumba", "ee-CHOOM-bah"),
            ("cyenda", "CHEHN-dah"),
            ("icumi", "ee-CHOO-mee"),
            ("umuceri", "oo-moo-CHEH-ree"),
            ("igiciro", "ee-gee-CHEE-roh"),
            ("rwacu", "RWAH-choo"),
        ],
    )
    def test_k_and_c(self, kinyarwanda, expected):
        assert word(kinyarwanda) == expected


class TestGlidesAndPalatals:
    @pytest.mark.parametrize(
        "kinyarwanda,expected",
        [
            # jy is the plain affricate, not j + y
            ("umujyi", "oo-MOO-jee"),
            ("kujya", "KOO-jah"),
            ("njya", "njah"),
            ("banjye", "BAHN-jeh"),
            # ny is ONE palatal nasal (canyon), and survives before /i/
            ("inyanya", "ee-NYAH-nyah"),
            ("nyogokuru", "nyoh-goh-KOO-roo"),
            ("kunywa", "KOO-nywah"),
            ("gabanya", "gah-BAH-nyah"),
            # ry / by / my keep the glide, and drop it before /i/ where it is
            # redundant: `ryiza` is [rʲiːza], best read as "REE-zah"
            ("ibiryo", "ee-BEE-ryoh"),
            ("kurya", "KOO-ryah"),
            ("ryiza", "REE-zah"),
            ("byiza", "BEE-zah"),
            ("byose", "BYOH-seh"),
            ("ibyumba", "ee-BYOOM-bah"),
            ("imyaka", "ee-MYAH-kah"),
            # shy collapses to sh
            ("ibishyimbo", "ee-bee-SHEEM-boh"),
            ("biraryoshye", "bee-rah-RYOH-sheh"),
            # w-glides are one syllable: "mwah", never "moo-wah"
            ("umwana", "oo-MWAH-nah"),
            ("mwiriwe", "mwee-REE-weh"),
            ("umukobwa", "oo-moo-KOH-bwah"),
            ("twaje", "TWAH-jeh"),
            ("rwanda", "RWAHN-dah"),
        ],
    )
    def test_clusters(self, kinyarwanda, expected):
        assert word(kinyarwanda) == expected


class TestPrenasalised:
    """mb/nd/ng/nk/mp/nz/nt/ns are single onsets — but English readers cannot
    start a syllable with them, so the nasal is written as a coda when there is
    a syllable in the same word to carry it."""

    @pytest.mark.parametrize(
        "kinyarwanda,expected",
        [
            ("imbere", "eem-BEH-reh"),
            ("urutonde", "oo-roo-TOHN-deh"),
            ("ingofero", "een-goh-FEH-roh"),
            ("nkunda", "NKOON-dah"),
            ("sinkunda", "seen-KOON-dah"),
            ("inzu", "EEN-zoo"),
            ("abantu", "ah-BAHN-too"),
            ("iminsi", "ee-MEEN-see"),
            ("inshuti", "een-SHOO-tee"),
            ("wamfasha", "wahm-FAH-shah"),
            ("irindwi", "ee-REEN-dwee"),
            ("umuryango", "oo-moo-RYAHN-goh"),
            # the ts affricate splits the same way
            ("mwaramutse", "mwah-rah-MOOT-seh"),
            ("bihendutse", "bee-hehn-DOOT-seh"),
        ],
    )
    def test_nasal_moves_to_the_previous_syllable(self, kinyarwanda, expected):
        assert word(kinyarwanda) == expected

    @pytest.mark.parametrize(
        "kinyarwanda,expected",
        [
            ("ndashaka", "ndah-SHAH-kah"),
            ("ndya", "ndyah"),
            ("mbyuka", "MBYOO-kah"),
            ("ngwino", "NGWEE-noh"),
            ("nshaka", "NSHAH-kah"),
            ("nzagaruka", "nzah-gah-ROO-kah"),
            ("mpa", "mpah"),
            ("mfite", "MFEE-teh"),
        ],
    )
    def test_word_initially_there_is_nowhere_to_move_it(self, kinyarwanda, expected):
        assert word(kinyarwanda) == expected

    def test_ny_is_never_split_it_is_one_nasal(self):
        assert word("inyama") == "ee-NYAH-mah"  # not "een-YAH-mah"
        assert word("inyota") == "ee-NYOH-tah"


class TestVowels:
    @pytest.mark.parametrize(
        "kinyarwanda,expected",
        [("a", "ah"), ("e", "eh"), ("i", "ee"), ("o", "oh"), ("u", "oo")],
    )
    def test_the_five_vowels(self, kinyarwanda, expected):
        assert word(kinyarwanda) == expected

    def test_a_doubled_vowel_is_one_long_syllable_not_two(self):
        assert syllabify_word("saa") == ["saa"]
        assert word("saa") == "saah"
        assert "saah" in respell("Ni saa sita.")

    def test_long_vowels_across_the_board(self):
        assert word("baa") == "baah"
        assert word("bee") == "behh"
        assert word("bii") == "beee"
        assert word("boo") == "bohh"
        assert word("buu") == "booh"


class TestProminence:
    def test_high_tone_from_phoneme_ref_wins_over_the_default(self):
        # Muraho is mu-ra-HO: the H is on the FINAL syllable, not the penult.
        assert respell("Muraho!", syl("Muraho!", {2: "H"})) == "moo-rah-HOH!"

    def test_penultimate_is_the_default_when_no_tone_is_marked(self):
        assert respell("Murakoze", {"syllables": []}) == "moo-rah-KOH-zeh"
        assert respell("Murakoze", None) == "moo-rah-KOH-zeh"

    def test_the_question_rise_R_is_intonation_not_prominence(self):
        # "Uva he?" marks R on the final syllable — a phrase contour. Caps mean
        # "this syllable is high in the word", so R must not produce one.
        out = respell("Uva he?", syl("Uva he?", {2: "R"}))
        assert out == "OO-vah heh?"

    def test_monosyllabic_words_stay_flat(self):
        assert respell("mu ku na ni") == "moo koo nah nee"

    def test_prominence_is_per_word_not_per_sentence(self):
        assert respell("Mwiriwe neza.") == "mwee-REE-weh NEH-zah."

    def test_a_capital_covers_the_moved_nasal_too(self):
        assert word("ikinyarwanda") == "ee-chee-nyah-RWAHN-dah"  # RWAHN, not RWAH


class TestSentencesAndPunctuation:
    @pytest.mark.parametrize(
        "sentence,expected",
        [
            ("Mwaramutse!", "mwah-rah-MOOT-seh!"),
            ("Amakuru yawe?", "ah-mah-KOO-roo YAH-weh?"),
            ("Ni meza, urakoze.", "nee MEH-zah, oo-rah-KOH-zeh."),
            ("Ijoro ryiza.", "ee-JOH-roh REE-zah."),
            ("Urakoze cyane.", "oo-rah-KOH-zeh CHAH-neh."),
            # Apostrophe clitics attach to their host: one syllable, not two
            ("Ikilo ry'inyanya", "ee-KEE-loh ree-NYAH-nyah"),
            ("Amafaranga y'u Rwanda", "ah-mah-fah-RAHN-gah yoo RWAHN-dah"),
            ("Ndifuza inyama n'ibirayi.", "ndee-FOO-zah ee-NYAH-mah nee-bee-RAH-yee."),
            # Two clauses: phoneme_ref only covers the first, the rest still works
            ("Ngwino, tugende.", "NGWEE-noh, too-GEHN-deh."),
        ],
    )
    def test_whole_sentences(self, sentence, expected):
        assert respell(sentence) == expected

    def test_punctuation_is_preserved_around_the_word(self):
        assert respell("«Muraho!»") == "«moo-rah-HOH!»"

    @pytest.mark.parametrize("junk", ["", "   ", "!!!", "— —", "?"])
    def test_nothing_pronounceable_yields_none(self, junk):
        assert respell(junk) is None

    @pytest.mark.parametrize("bad", [None, 42, [], {}])
    def test_non_string_input_is_survivable(self, bad):
        assert respell(bad) is None


class TestDegradedPhonemeRef:
    """phoneme_ref is data we did not write in this module; treat it as hostile."""

    @pytest.mark.parametrize(
        "ref",
        [
            None,
            {},
            {"syllables": []},
            {"syllables": None},
            {"syllables": "not a list"},
            {"syllables": [{"syl": "mwa"}]},          # tone key missing
            {"syllables": [{"tone": "H"}]},           # syl key missing
            {"syllables": ["mwa", "ra"]},             # not dicts
            {"syllables": [{"syl": "xx", "tone": "H"}] * 4},  # wrong sentence
            {"syllables": [{"syl": "mwa", "tone": "H"}] * 99},  # too long
        ],
    )
    def test_falls_back_to_the_rules_without_raising(self, ref):
        out = respell("Mwaramutse!", ref)
        assert out and out.lower() == "mwah-rah-moot-seh!"

    def test_a_mismatched_prefix_stops_trusting_the_rest(self):
        # First syllable matches and is H; the second does not match, so no
        # tone from that point on — and certainly no capital on the wrong one.
        ref = {"syllables": [{"syl": "mwa", "tone": "H"}, {"syl": "zz", "tone": "H"}]}
        assert respell("Mwaramutse", ref) == "MWAH-rah-moot-seh"


class TestPerWordApi:
    def test_words_align_one_to_one_with_the_input(self):
        sentence = "Ni meza, urakoze."
        out = respell_words(sentence, syl(sentence))
        assert [w.word for w in out] == sentence.split()
        assert [w.pronunciation for w in out] == ["nee", "MEH-zah,", "oo-rah-KOH-zeh."]
        assert out[0].as_dict() == {"word": "Ni", "pronunciation": "nee"}

    def test_unpronounceable_tokens_report_none_rather_than_vanishing(self):
        out = respell_words("Muraho — Mwiriwe")
        assert [w.word for w in out] == ["Muraho", "—", "Mwiriwe"]
        assert out[1].pronunciation is None

    def test_the_joined_words_are_the_sentence_respelling(self):
        for item in SEEDED_ITEMS:
            parts = respell_words(item["sentence"], item["phoneme_ref"])
            joined = " ".join(p.pronunciation for p in parts if p.pronunciation)
            assert joined == respell(item["sentence"], item["phoneme_ref"])


class TestOverrides:
    """Loanwords keep their source consonants: they are not palatalised."""

    @pytest.mark.parametrize(
        "kinyarwanda,expected",
        [
            ("banki", "BAHN-kee"),      # not "BAHN-chee"
            ("ikilo", "ee-KEE-loh"),    # not "ee-CHEE-loh"
            ("itike", "ee-TEE-keh"),    # not "ee-TEE-cheh"
            ("Kigali", "kee-GAH-lee"),
            ("Kimironko", "kee-mee-ROHN-koh"),
        ],
    )
    def test_loanwords(self, kinyarwanda, expected):
        assert word(kinyarwanda) == expected

    def test_an_override_beats_phoneme_ref(self):
        wrong = {"syllables": [{"syl": "ba", "tone": "H"}, {"syl": "nki", "tone": "H"}]}
        assert respell("banki", wrong) == "BAHN-kee"

    def test_overrides_survive_capitalisation_and_punctuation(self):
        assert respell("Ntuye i Kigali.") == "NTOO-yeh ee kee-GAH-lee."

    def test_every_override_is_a_plausible_respelling(self):
        for key, value in OVERRIDES.items():
            assert key == key.lower(), key
            assert re.fullmatch(r"[a-zA-Z]+(-[a-zA-Z]+)*", value), (key, value)


class TestSharedWithTheSeed:
    """The syllabifier here IS the one seed/data_kin.py builds phoneme_ref with.
    If they ever diverge, every tone mark silently lands on the wrong syllable."""

    def test_seeded_phoneme_ref_is_this_modules_syllabification(self):
        for item in SEEDED_ITEMS:
            stored = [s["syl"] for s in item["phoneme_ref"]["syllables"]]
            assert stored == syllabify(item["sentence"]), item["sentence"]

    def test_the_head_is_the_span_phoneme_ref_covers(self):
        assert syllabify("Ni meza, urakoze.") == ["ni", "me", "za"]
        assert syllabify_word("rw'ibiryo") == ["rw", "i", "bi", "ryo"]


class TestTheWholeSeededCorpus:
    """158 items, run end to end. These are properties, not spot checks."""

    def test_every_item_respells(self):
        for item in SEEDED_ITEMS:
            out = respell(item["sentence"], item["phoneme_ref"])
            assert out, item["sentence"]

    def test_output_stays_inside_the_agreed_alphabet(self):
        # Letters, hyphens, spaces and whatever punctuation the source had.
        for item in SEEDED_ITEMS:
            out = respell(item["sentence"], item["phoneme_ref"])
            assert not re.search(r"[^a-zA-Z\s\-'’!?.,«»…]", out), (item["sentence"], out)

    def test_no_kinyarwanda_only_spellings_leak_through(self):
        # If any of these survive into the output, a rule failed to fire.
        for item in SEEDED_ITEMS:
            out = respell(item["sentence"], item["phoneme_ref"]).lower()
            for leak in ("cy", "jy", "shy", "ky", "ntw"):
                assert leak not in out, (item["sentence"], out, leak)

    def test_a_word_respells_the_same_way_in_every_item_it_appears_in(self):
        # A learner who meets `angahe` in two lessons must see one respelling.
        seen: dict[str, set[str]] = {}
        for item in SEEDED_ITEMS:
            for part in respell_words(item["sentence"], item["phoneme_ref"]):
                key = re.sub(r"[^a-z']", "", part.word.lower())
                if key and part.pronunciation:
                    bare = re.sub(r"^[^a-zA-Z]+|[^a-zA-Z]+$", "", part.pronunciation)
                    seen.setdefault(key, set()).add(bare)
        assert {k: v for k, v in seen.items() if len(v) > 1} == {}

    def test_deterministic(self):
        for item in SEEDED_ITEMS[:20]:
            a = respell(item["sentence"], item["phoneme_ref"])
            b = respell(item["sentence"], item["phoneme_ref"])
            assert a == b

    def test_syllable_count_is_preserved_or_reduced_never_invented(self):
        # Hyphenated groups may only be FEWER than the stored syllables (a
        # clitic merges into its host); a respelling must never add one.
        for item in SEEDED_ITEMS:
            stored = len(item["phoneme_ref"]["syllables"])
            if stored == 0:
                continue
            head = re.split(r"[,.!?…]", item["sentence"])[0]
            out = respell(head, item["phoneme_ref"])
            groups = sum(len(w.split("-")) for w in out.split())
            assert groups <= stored, (item["sentence"], out)


def test_the_uncertainty_list_is_not_empty_and_says_what_it_means():
    assert len(NEEDS_NATIVE_REVIEW) >= 5
    assert any("tone" in note.lower() for note in NEEDS_NATIVE_REVIEW)
