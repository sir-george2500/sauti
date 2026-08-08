"""FakeLlmClient — scripted double for the two AI surfaces:

- conversation practice: the single forced-JSON `respond` call;
- the study buddy: the bounded `say` / info-tool loop.

Both branch on the conversation STATE they are handed (which tools are on the
call, whether tool results have come back yet) rather than a call counter — so
the script also asserts that the loop appends tool results correctly.

Used when SAUTI_FAKE_AI=1 and in every test. Never calls the network.
"""
from __future__ import annotations

import json
import uuid

from sauti.llm.client import LlmTurn, TokenUsage, ToolCall, ToolSpec

# Buddy triggers: words that make the scripted buddy go and fetch real rows
# before speaking (so e2e proves the grounded path, not just the canned one).
BUDDY_REVIEW_HINTS = ("review", "due", "waiting", "next", "what should", "practice")


def _call(name: str, args: dict) -> ToolCall:
    return ToolCall(id=f"call_{uuid.uuid4().hex[:8]}", name=name, arguments_json=json.dumps(args))


def _usage(messages: list[dict], args: dict) -> TokenUsage:
    """Rough deterministic token estimate so metering paths are exercised."""
    prompt_chars = sum(len(str(m.get("content") or "")) for m in messages)
    return TokenUsage(
        model="fake",
        prompt_tokens=max(1, prompt_chars // 4),
        completion_tokens=max(1, len(json.dumps(args)) // 4),
        cached_prompt_tokens=0,
    )


class FakeLlmClient:
    async def complete(
        self,
        messages: list[dict],
        tools: list[ToolSpec] | None = None,
        tool_choice: str | None = None,
        max_tokens: int | None = None,
    ) -> LlmTurn:
        user_msgs = [m for m in messages if m.get("role") == "user"]
        last_user = (user_msgs[-1]["content"] if user_msgs else "") or ""
        lowered = last_user.lower()

        if any(t.name == "say" for t in tools or []):
            return self._buddy(messages, lowered)

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
            # Rough deterministic token estimate so metering paths are exercised.
            prompt_chars = sum(len(str(m.get("content") or "")) for m in messages)
            usage = TokenUsage(
                model="fake",
                prompt_tokens=max(1, prompt_chars // 4),
                completion_tokens=len(json.dumps(args)) // 4,
                cached_prompt_tokens=0,
            )
            return LlmTurn(tool_calls=[_call("respond", args)], usage=usage)

        # Untooled call — plain content (no surface uses this today).
        return LlmTurn(
            content="Muraho neza! Urashaka iki ku isoko?\nEN: Hello! What would you like at the market?"
        )

    # -- study buddy -------------------------------------------------------
    def _buddy(self, messages: list[dict], lowered: str) -> LlmTurn:
        """Two scripted shapes, chosen by state:

        1. no tool results yet + the learner asked about work waiting for them
           → fetch the real rows first (get_due_reviews);
        2. otherwise → speak, quoting whatever the tools actually returned.

        Every reply carries one navigate action so the frontend's action chips
        are exercised end to end under SAUTI_FAKE_AI=1.
        """
        tool_msgs = [m for m in messages if m.get("role") == "tool"]

        if not tool_msgs and any(h in lowered for h in BUDDY_REVIEW_HINTS):
            args = {"limit": 8}
            return LlmTurn(
                tool_calls=[_call("get_due_reviews", args)], usage=_usage(messages, args)
            )

        text = (
            "Muraho, my friend! I am Mwarimu — ask me what is waiting for you and I "
            "will dig it up. Twige! (Let's study!)"
        )
        gloss = "Let's study!"
        grounded = self._first_due_item(tool_msgs)
        if grounded is not None:
            sentence, item_gloss, due_count = grounded
            text = (
                f"Yego! You have {due_count} sentence(s) waiting — start with "
                f"“{sentence}” ({item_gloss}). Turabikora! (We've got this!)"
            )
            gloss = "We've got this!"

        args = {
            "text": text,
            "gloss": gloss,
            "actions": [{"href": "/progress", "label": "Show me my progress"}],
        }
        return LlmTurn(tool_calls=[_call("say", args)], usage=_usage(messages, args))

    @staticmethod
    def _first_due_item(tool_msgs: list[dict]) -> tuple[str, str, int] | None:
        """Quote a REAL row out of the last tool result — never an invented one."""
        for msg in reversed(tool_msgs):
            try:
                payload = json.loads(msg.get("content") or "{}")
            except json.JSONDecodeError:
                continue
            items = payload.get("items") if isinstance(payload, dict) else None
            if isinstance(items, list) and items:
                first = items[0]
                return (
                    str(first.get("sentence") or ""),
                    str(first.get("gloss") or ""),
                    int(payload.get("due_count") or len(items)),
                )
        return None
