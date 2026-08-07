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
class LlmTurn:
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)

    def wants_tools(self) -> bool:
        return bool(self.tool_calls)


@runtime_checkable
class LlmClient(Protocol):
    async def complete(
        self,
        messages: list[dict],
        tools: list[ToolSpec] | None = None,
        tool_choice: str | None = None,
    ) -> LlmTurn:
        """messages: OpenAI chat format dicts. tool_choice: tool name to force, or None."""
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
