"""FakeLlmClient — scripted double for the single forced-JSON `respond` call
(one call per learner turn, mirroring the real prompt contract).

Used when SAUTI_FAKE_AI=1 and in every test. Never calls the network.
"""
from __future__ import annotations

import json
import uuid

from sauti.llm.client import LlmTurn, ToolCall, ToolSpec


def _call(name: str, args: dict) -> ToolCall:
    return ToolCall(id=f"call_{uuid.uuid4().hex[:8]}", name=name, arguments_json=json.dumps(args))


class FakeLlmClient:
    async def complete(
        self,
        messages: list[dict],
        tools: list[ToolSpec] | None = None,
        tool_choice: str | None = None,
    ) -> LlmTurn:
        user_msgs = [m for m in messages if m.get("role") == "user"]
        last_user = (user_msgs[-1]["content"] if user_msgs else "") or ""
        lowered = last_user.lower()

        if tool_choice == "respond":
            if "angahe" in lowered or "price" in lowered:
                reply = "Ikilo cy'inyanya ni amafaranga magana atanu."
                gloss = "A kilo of tomatoes is five hundred francs."
                goals_met = ["ask a price"]
            else:
                reply = "Muraho neza! Urashaka iki ku isoko?"
                gloss = "Hello! What would you like at the market?"
                goals_met = []
            corrections = []
            if "muraho" not in lowered and len(last_user) > 3:
                corrections.append(
                    {
                        "what": "Greeting form",
                        "why": "",
                        "fix": 'Try opening with "Muraho!" — a warm all-purpose greeting.',
                    }
                )
            args = {
                "reply": reply,
                "gloss": gloss,
                "praise": "Byiza cyane! You are making yourself understood.",
                "correction_candidates": corrections,
                "goals_met": goals_met,
            }
            return LlmTurn(tool_calls=[_call("respond", args)])

        # Untooled call — plain content (no surface uses this today).
        return LlmTurn(
            content="Muraho neza! Urashaka iki ku isoko?\nEN: Hello! What would you like at the market?"
        )
