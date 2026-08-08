"""Language segmentation — the pure piece the mixed-voice clip is built on.

If this regresses, Kinyarwanda gets read aloud by an English voice in a
pronunciation-teaching app, so the table below is deliberately exhaustive.
"""
from __future__ import annotations

import pytest

from sauti.speech.segmentation import (
    EN,
    MARKERS,
    RW,
    Segment,
    normalize,
    segment_reply,
    segments_payload,
)

CURRICULUM = [
    "Mwaramutse!",
    "Mwiriwe.",
    "Ndashaka ikilo cy'inyanya.",
    "Ni amafaranga angahe?",
]


def langs(text: str, known=CURRICULUM) -> list[str]:
    return [s.lang for s in segment_reply(text, known)]


def texts(text: str, known=CURRICULUM) -> list[str]:
    return [s.text for s in segment_reply(text, known)]


class TestNormalize:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Mwaramutse!", "mwaramutse"),
            ("  MWIRIWE .  ", "mwiriwe"),
            ("Ndashaka ikilo cy'inyanya.", "ndashaka ikilo cy inyanya"),
            ("", ""),
            ("!!! ???", ""),
        ],
    )
    def test_lowercase_strip_punctuation_collapse_space(self, raw, expected):
        assert normalize(raw) == expected


class TestSegmentReply:
    def test_the_owners_example_switches_voice_mid_reply(self):
        reply = (
            "Today you learned greetings! For example, 'Mwaramutse' means "
            "'Good morning!' and 'Mwiriwe' means 'Good afternoon.'"
        )
        segments = segment_reply(reply, CURRICULUM)
        assert [s.lang for s in segments] == [EN, RW, EN, RW, EN]
        assert segments[1].text == "Mwaramutse"
        assert segments[3].text == "Mwiriwe"
        # The quoted English gloss is NOT Kinyarwanda just because it is quoted.
        assert "Good morning!" in segments[2].text
        assert "Good afternoon." in segments[4].text
        # Nothing pronounceable was lost.
        assert "Today you learned greetings!" in segments[0].text

    def test_all_english_is_one_english_span(self):
        reply = "Nice work today — you are three lessons from the end of this unit."
        assert segment_reply(reply, CURRICULUM) == [Segment(reply, EN)]

    def test_all_kinyarwanda_is_one_rw_span(self):
        assert segment_reply("Muraho! Amakuru?", CURRICULUM) == [
            Segment("Muraho! Amakuru?", RW)
        ]

    def test_quoted_curriculum_sentence_is_rw_even_without_markers(self):
        # No marker word in it at all — only the curriculum row makes it rw.
        out = segment_reply("Try \"Ni amafaranga angahe?\" next.", CURRICULUM)
        assert [s.lang for s in out] == [EN, RW, EN]
        assert out[1].text == "Ni amafaranga angahe?"

    def test_quoted_sentence_not_in_curriculum_and_without_markers_stays_english(self):
        out = segment_reply('She said "the market closes at six".', CURRICULUM)
        assert [s.lang for s in out] == [EN]

    @pytest.mark.parametrize(
        "opener,closer",
        [("'", "'"), ('"', '"'), ("“", "”"), ("‘", "’"), ("«", "»")],
    )
    def test_every_quote_flavour_is_recognised(self, opener, closer):
        out = segment_reply(f"Say {opener}Mwaramutse{closer} in the morning.", CURRICULUM)
        assert [s.lang for s in out] == [EN, RW, EN]
        assert out[1].text == "Mwaramutse"

    def test_curly_quotes_nested_inside_straight_quotes(self):
        out = segment_reply('He wrote: "she said “Mwiriwe” back".', CURRICULUM)
        assert RW in [s.lang for s in out]
        assert any(s.text == "Mwiriwe" for s in out)

    def test_in_word_apostrophes_do_not_open_a_quote(self):
        # cy'inyanya / don't — a naive quote scanner swallows the rest here.
        out = segment_reply(
            "Don't forget \"Ndashaka ikilo cy'inyanya.\" — it is due today.",
            CURRICULUM,
        )
        assert [s.lang for s in out] == [EN, RW, EN]
        assert out[1].text == "Ndashaka ikilo cy'inyanya."
        assert out[0].text.startswith("Don't forget")

    def test_unquoted_marker_word_is_rw(self):
        out = segment_reply("Muraho, my friend! Ask me anything.", CURRICULUM)
        assert [s.lang for s in out] == [RW, EN]
        assert out[0].text == "Muraho,"
        assert out[1].text == "my friend! Ask me anything."

    def test_adjacent_same_language_spans_merge(self):
        out = segment_reply("Yego! Muraho! You did it.", CURRICULUM)
        assert [s.lang for s in out] == [RW, EN]
        assert out[0].text == "Yego! Muraho!"

    def test_two_quoted_rw_spans_separated_only_by_punctuation_merge(self):
        out = segment_reply('"Mwaramutse" "Mwiriwe"', CURRICULUM)
        assert out == [Segment("Mwaramutse Mwiriwe", RW)]

    def test_punctuation_only_spans_are_dropped(self):
        out = segment_reply('— "Mwaramutse" … !', CURRICULUM)
        assert out == [Segment("Mwaramutse", RW)]

    @pytest.mark.parametrize("reply", ["", "   ", "\n\t ", "!!!", "— … —", None, 42])
    def test_nothing_to_say_is_no_segments(self, reply):
        assert segment_reply(reply, CURRICULUM) == []

    def test_unclosed_quote_does_not_swallow_the_reply(self):
        out = segment_reply('She said "Mwaramutse and left the room.', CURRICULUM)
        assert [s.lang for s in out] == [EN, RW, EN]  # marker still caught, as a word
        assert out[1].text == '"Mwaramutse'  # verbatim: nothing pronounceable is lost
        assert out[2].text == "and left the room."

    def test_empty_quotes_are_not_a_span(self):
        assert segment_reply('He said "" and left.', CURRICULUM) == [
            Segment('He said "" and left.', EN)
        ]

    def test_known_sentences_may_be_empty(self):
        # With no curriculum at all the marker list still has to carry greetings.
        out = segment_reply("Say 'Mwaramutse' first.", [])
        assert [s.lang for s in out] == [EN, RW, EN]

    def test_unknown_quoted_kinyarwanda_without_markers_needs_the_curriculum(self):
        reply = "Try 'Ndashaka ikilo cy\\'inyanya.' today."
        assert RW not in langs(reply, [])  # honest: we do not guess
        assert RW in langs("Try \"Ndashaka ikilo cy'inyanya.\" today.", CURRICULUM)

    def test_it_is_deterministic_and_side_effect_free(self):
        reply = "Muraho! Today: 'Mwiriwe' means 'Good afternoon.'"
        known = list(CURRICULUM)
        first = segment_reply(reply, known)
        second = segment_reply(reply, known)
        assert first == second
        assert known == CURRICULUM  # the caller's list is untouched

    def test_every_marker_is_detected_standalone(self):
        for marker in MARKERS:
            assert segment_reply(marker.capitalize(), []) == [
                Segment(marker.capitalize(), RW)
            ], marker

    def test_markers_are_case_and_punctuation_insensitive(self):
        assert langs("MURAKOZE!!! thanks for asking.", []) == [RW, EN]

    def test_payload_is_the_wire_shape(self):
        payload = segments_payload(segment_reply("Say 'Mwaramutse' now.", CURRICULUM))
        assert payload == [
            {"text": "Say", "lang": EN},
            {"text": "Mwaramutse", "lang": RW},
            {"text": "now.", "lang": EN},
        ]

    def test_a_long_reply_stays_a_handful_of_spans(self):
        """Every span is one engine call — segmentation must not shred a reply."""
        reply = (
            "Yego! You have three sentences waiting — start with "
            "\"Mwaramutse!\" (Good morning) and then \"Mwiriwe.\" "
            "(Good afternoon). Turabikora!"
        )
        out = segment_reply(reply, CURRICULUM)
        assert len(out) <= 7
        assert [s.lang for s in out][:2] == [RW, EN]
