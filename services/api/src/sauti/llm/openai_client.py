"""Hand-rolled OpenAI chat/completions client over httpx — no SDK needed."""
from __future__ import annotations

import httpx

from sauti.errors import ApiError
from sauti.llm.client import LlmClient, LlmTurn, TokenUsage, ToolCall, ToolSpec

OPENAI_URL = "https://api.openai.com/v1/chat/completions"


class OpenAiLlmClient:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", timeout_s: float = 30.0):
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_s
        # One pooled client for the app's lifetime: a conversation turn makes
        # 2-4 sequential calls — re-handshaking TLS each time is pure latency.
        self._client: httpx.AsyncClient | None = None

    def _http(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def aclose(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    async def complete(
        self,
        messages: list[dict],
        tools: list[ToolSpec] | None = None,
        tool_choice: str | None = None,
        max_tokens: int | None = None,
    ) -> LlmTurn:
        if not self._api_key:
            raise ApiError(503, "AI_UNAVAILABLE", "AI is not configured")
        # max_tokens: a conversation turn is 1–2 short sentences plus a small
        # JSON envelope (~120-150 tokens observed); 220 bounds runaway spend
        # while leaving comfortable headroom. Callers with a tighter budget
        # (the buddy bubble) pass their own.
        body: dict = {
            "model": self._model,
            "messages": messages,
            "temperature": 0.6,
            "max_tokens": max_tokens or 220,
        }
        if tools:
            body["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in tools
            ]
        if tool_choice in ("auto", "required", "none"):
            # "required" = call SOME tool. Left unforced, gpt-4o-mini happily
            # answers in prose (markdown links and all) and the structured
            # envelope — gloss, validated actions — never arrives.
            body["tool_choice"] = tool_choice
        elif tool_choice:
            body["tool_choice"] = {"type": "function", "function": {"name": tool_choice}}
        try:
            resp = await self._http().post(
                OPENAI_URL,
                json=body,
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ApiError(502, "AI_ERROR", f"AI backend failed: {type(exc).__name__}")
        data = resp.json()
        msg = data["choices"][0]["message"]
        tool_calls = [
            ToolCall(
                id=c["id"],
                name=c["function"]["name"],
                arguments_json=c["function"]["arguments"] or "{}",
            )
            for c in (msg.get("tool_calls") or [])
        ]
        u = data.get("usage") or {}
        usage = TokenUsage(
            model=str(data.get("model") or self._model),
            prompt_tokens=int(u.get("prompt_tokens") or 0),
            completion_tokens=int(u.get("completion_tokens") or 0),
            cached_prompt_tokens=int(
                (u.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
            ),
        )
        return LlmTurn(content=msg.get("content"), tool_calls=tool_calls, usage=usage)
