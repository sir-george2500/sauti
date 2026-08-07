"""OpenAI's automatic prompt cache discounts an exact-match prompt PREFIX.

The system prompt therefore contains ONLY static content (persona, rules,
scenario goals, scenario vocab) and must be byte-identical across every turn
of a conversation — per-turn dynamic content (history, learner message) rides
behind it in the message list.
"""
from __future__ import annotations

from sauti.models import Scenario
from sauti.services.conversation import build_system_prompt


def _scenario() -> Scenario:
    return Scenario(
        title="Kimironko market run",
        setting="Kimironko market, Kigali",
        persona={
            "name": "Mukamana",
            "role": "vegetable vendor",
            "description": "Warm and quick-witted.",
            "situation_tag": "market",
        },
        goals=["greet the vendor", "ask a price"],
        min_cefr="A1",
    )


VOCAB = [
    {"sentence": "Muraho!", "gloss": "Hello!"},
    {"sentence": "Ni angahe?", "gloss": "How much is it?"},
]


class TestStaticPromptPrefix:
    def test_byte_identical_for_same_inputs(self):
        a = build_system_prompt(_scenario(), "A1", list(VOCAB))
        b = build_system_prompt(_scenario(), "A1", list(VOCAB))
        assert a == b  # exact-prefix match is what earns the cache discount

    def test_contains_only_static_content(self):
        prompt = build_system_prompt(_scenario(), "A1", VOCAB)
        # Persona, rules, goals and vocab are all present…
        assert "Mukamana" in prompt
        assert "greet the vendor" in prompt
        assert "Ni angahe? — How much is it?" in prompt
        assert "respond tool" in prompt
        # …and nothing per-turn is: no timestamps, no turn counters.
        import re

        assert not re.search(r"\d{4}-\d{2}-\d{2}", prompt)
        assert "turn 1" not in prompt.lower()

    def test_vocab_order_matters_and_is_preserved(self):
        """The prompt embeds vocab in the given (deterministic DB) order — a
        reordering would silently break the byte-identical prefix."""
        reversed_vocab = list(reversed(VOCAB))
        assert build_system_prompt(_scenario(), "A1", VOCAB) != build_system_prompt(
            _scenario(), "A1", reversed_vocab
        )
