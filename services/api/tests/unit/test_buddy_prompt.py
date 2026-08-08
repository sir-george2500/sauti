"""Mwarimu's prompt prefix and href validator.

Two properties this file protects:

1. system[0] is BYTE-IDENTICAL for every user and every turn. OpenAI's
   automatic prompt cache discounts an exact-match prefix, so anything
   per-learner (the snapshot) has to live behind it, in system[1].
2. `parse_href` is total and closed: only the six in-app shapes survive, and
   nothing that reaches it can escape the app (scheme, host, traversal,
   query strings). Existence checks come after, against the DB.
"""
from __future__ import annotations

import re

import pytest

from sauti.services.buddy import (
    MAX_HISTORY_TURNS,
    MAX_TEXT_CHARS,
    MAX_TOKENS,
    STATIC_SYSTEM_PROMPT,
    parse_href,
    plain_text,
    render_snapshot,
)

SNAPSHOT = {
    "cefr": "A1",
    "unit_title": "Ku isoko",
    "unit_ord": 2,
    "situation_tag": "market",
    "lesson_title": "Kubaza igiciro",
    "lesson_id": "2f9c1e6a-1111-4111-8111-111111111111",
    "lessons_left_in_unit": 2,
    "due_reviews": 8,
    "active_days": 5,
    "window_days": 14,
    "daily_goal_minutes": 25,
}


class TestStaticPrefix:
    def test_prompt_is_a_module_constant_not_a_builder(self):
        """No f-string over per-learner data can sneak in: the cached prefix is
        one immutable string, identical for every connection."""
        assert isinstance(STATIC_SYSTEM_PROMPT, str)
        assert STATIC_SYSTEM_PROMPT == STATIC_SYSTEM_PROMPT.strip()

    def test_contains_persona_and_grounding_rules_only(self):
        assert "Mwarimu" in STATIC_SYSTEM_PROMPT
        assert "NEVER invent Kinyarwanda" in STATIC_SYSTEM_PROMPT
        assert "say tool exactly once" in STATIC_SYSTEM_PROMPT
        # …and nothing per-learner or per-turn:
        assert not re.search(r"\d{4}-\d{2}-\d{2}", STATIC_SYSTEM_PROMPT)
        for leak in ("A1", "due", "Unit ", "turn 1"):
            assert leak not in STATIC_SYSTEM_PROMPT.replace("reviews", "")

    def test_learner_data_lives_in_the_snapshot_message(self):
        rendered = render_snapshot(SNAPSHOT)
        assert "Unit 2 — Ku isoko" in rendered
        assert "Kubaza igiciro" in rendered
        assert "8" in rendered
        assert rendered != STATIC_SYSTEM_PROMPT
        # The snapshot advertises hrefs the model may reuse — real ids only.
        assert "/lesson/2f9c1e6a-1111-4111-8111-111111111111" in rendered
        assert "/vocab/market" in rendered

    def test_snapshot_render_is_deterministic(self):
        assert render_snapshot(SNAPSHOT) == render_snapshot(dict(SNAPSHOT))

    def test_snapshot_never_claims_minutes_done_today(self):
        """Minutes-done-today is not computable server-side; the prompt says so
        rather than letting the model invent a number."""
        assert "never claim a number" in render_snapshot(SNAPSHOT)

    def test_cost_caps_are_tight(self):
        assert MAX_TOKENS <= 180
        assert MAX_HISTORY_TURNS == 6
        assert MAX_TEXT_CHARS == 500


class TestHrefValidator:
    LESSON = "/lesson/2f9c1e6a-1111-4111-8111-111111111111"

    @pytest.mark.parametrize(
        "href,expected",
        [
            ("/notebook", ("static", "/notebook")),
            ("/progress", ("static", "/progress")),
            ("/roadmap", ("static", "/roadmap")),
            ("/vocab/market", ("vocab", "market")),
            (LESSON, ("lesson", "2f9c1e6a-1111-4111-8111-111111111111")),
            (
                "/practice/conversation/2f9c1e6a-1111-4111-8111-111111111111",
                ("scenario", "2f9c1e6a-1111-4111-8111-111111111111"),
            ),
            (
                "/practice/pronunciation/2f9c1e6a-1111-4111-8111-111111111111",
                ("item", "2f9c1e6a-1111-4111-8111-111111111111"),
            ),
        ],
    )
    def test_accepts_the_six_in_app_shapes(self, href, expected):
        assert parse_href(href) == expected

    @pytest.mark.parametrize(
        "href",
        [
            "",
            "   ",
            "/",
            "/lesson/not-a-uuid",
            "/lesson/",
            "/lesson/2f9c1e6a-1111-4111-8111-111111111111/edit",
            "/vocab/market?x=1",
            "/vocab/../../etc/passwd",
            "/vocab/Market",  # tags are lowercase snake in the DB
            "//evil.com/progress",
            "https://evil.com/progress",
            "javascript:alert(1)",
            "/progress#x",
            "/admin",
            "/practice/listening/2f9c1e6a-1111-4111-8111-111111111111",
            "notebook",
        ],
    )
    def test_rejects_everything_else(self, href):
        assert parse_href(href) is None

    @pytest.mark.parametrize("href", [None, 42, {"href": "/progress"}, ["/progress"]])
    def test_is_total_on_non_strings(self, href):
        assert parse_href(href) is None

    def test_surrounding_whitespace_is_tolerated(self):
        assert parse_href("  /progress  ") == ("static", "/progress")


class TestPlainText:
    """The chat bubble is plain text. The prompt forbids markdown; observed
    live, gpt-4o-mini still emits **bold** and [label](/href) now and then."""

    def test_link_collapses_to_its_label(self):
        assert (
            plain_text("Ready? [Take me to those eight reviews](/vocab/family)")
            == "Ready? Take me to those eight reviews"
        )

    def test_emphasis_and_code_marks_are_stripped(self):
        assert plain_text("You learned **Mwaramutse** and `Mwiriwe`") == (
            "You learned Mwaramutse and Mwiriwe"
        )

    def test_a_list_becomes_one_paragraph(self):
        assert plain_text("Waiting:\n1. Muraho\n- Amakuru yawe?\n") == (
            "Waiting: Muraho Amakuru yawe?"
        )

    def test_kinyarwanda_punctuation_survives(self):
        for line in ("Ikilo cy'inyanya ni angahe?", "Abana bakinira ku rugo.", "Twige!"):
            assert plain_text(line) == line

    def test_empty_input_is_empty_output(self):
        assert plain_text("") == ""
        assert plain_text("   \n  ") == ""
