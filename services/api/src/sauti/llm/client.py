"""LlmClient seam — the only interface the rest of the app knows (rent-rwanda pattern)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict  # JSON Schema


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments_json: str


@dataclass(frozen=True)
class TokenUsage:
    """The provider's usage payload for ONE real call — the raw material for
    sauti.llm_usage metering. cached_prompt_tokens is OpenAI's
    prompt_tokens_details.cached_tokens (the discounted prefix)."""

    model: str
    prompt_tokens: int
    completion_tokens: int
    cached_prompt_tokens: int = 0


@dataclass(frozen=True)
class LlmTurn:
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: TokenUsage | None = None

    def wants_tools(self) -> bool:
        return bool(self.tool_calls)


@runtime_checkable
class LlmClient(Protocol):
    async def complete(
        self,
        messages: list[dict],
        tools: list[ToolSpec] | None = None,
        tool_choice: str | None = None,
        max_tokens: int | None = None,
    ) -> LlmTurn:
        """messages: OpenAI chat format dicts. tool_choice: tool name to force, or None.

        max_tokens caps the completion for this call (surfaces differ: a
        conversation turn is a JSON envelope, a buddy bubble is a sentence);
        None keeps the client's default.
        """
        ...


def system(content: str) -> dict:
    return {"role": "system", "content": content}


def user(content: str) -> dict:
    return {"role": "user", "content": content}


def assistant_with_tools(content: str | None, tool_calls: list[ToolCall]) -> dict:
    return {
        "role": "assistant",
        "content": content,
        "tool_calls": [
            {
                "id": c.id,
                "type": "function",
                "function": {"name": c.name, "arguments": c.arguments_json},
            }
            for c in tool_calls
        ],
    }


def tool_result(call_id: str, content_json: str) -> dict:
    return {"role": "tool", "tool_call_id": call_id, "content": content_json}
