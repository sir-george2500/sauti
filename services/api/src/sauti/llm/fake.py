"""FakeLlmClient — scripted double, branches on the conversation state it is handed
(not a call counter), which also asserts the loop appends tool results correctly.

Used when SAUTI_FAKE_AI=1 and in every test. Never calls the network.
"""
from __future__ import annotations

import json
import uuid

from sauti.llm.client import LlmClient, LlmTurn, ToolCall, ToolSpec


def _call(name: str, args: dict) -> ToolCall:
    return ToolCall(id=f"call_{uuid.uuid4().hex[:8]}", name=name, arguments_json=json.dumps(args))


class FakeLlmClient:
    async def complete(
        self,
        messages: list[dict],
        tools: list[ToolSpec] | None = None,
        tool_choice: str | None = None,
    ) -> LlmTurn:
        tool_names = {t.name for t in (tools or [])}
        user_msgs = [m for m in messages if m.get("role") == "user"]
        tool_msgs = [m for m in messages if m.get("role") == "tool"]
        last_user = (user_msgs[-1]["content"] if user_msgs else "") or ""

        # Forced structured coach extraction — single call, no loop.
        if tool_choice == "coach_feedback" or (
            tool_choice and tool_choice in tool_names and "coach" in tool_choice
        ):
            corrections = []
            if "muraho" not in last_user.lower() and len(last_user) > 3:
                corrections.append(
                    {
                        "title": "Greeting form",
                        "body": 'Try opening with "Muraho!" — a warm all-purpose greeting.',
                    }
                )
            args = {"praise": "Byiza cyane! You are making yourself understood.",
                    "corrections": corrections}
            return LlmTurn(tool_calls=[_call(tool_choice or "coach_feedback", args)])

        # Partner loop. First pass of a turn: ground in scenario vocab (and mark a
        # goal when the learner asks a price). Once tool results are in: final text.
        if not tool_msgs:
            calls = []
            if "get_scenario_vocab" in tool_names:
                calls.append(_call("get_scenario_vocab", {}))
            lowered = last_user.lower()
            if "mark_goal_met" in tool_names and ("angahe" in lowered or "price" in lowered):
                calls.append(_call("mark_goal_met", {"goal": "ask a price"}))
            if calls:
                return LlmTurn(tool_calls=calls)

        if "angahe" in last_user.lower():
            return LlmTurn(
                content="Ikilo cy'inyanya ni amafaranga magana atanu.\nEN: A kilo of tomatoes is five hundred francs."
            )
        return LlmTurn(content="Muraho neza! Urashaka iki ku isoko?\nEN: Hello! What would you like at the market?")
