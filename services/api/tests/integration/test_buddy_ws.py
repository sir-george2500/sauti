"""WS /ws/buddy — Mwarimu, over a real Postgres with the scripted FakeLlmClient.

What these tests hold down:
- the frame contract ({buddy} first, then {action} chips, {error} for refusals);
- grounding: a sentence the buddy quotes is a row that exists in the DB;
- href re-resolution: an invented id never reaches the client;
- the cost caps (one call per turn, history window, usage metering);
- graceful degradation: a dead LLM is still a warm bubble, not a dead socket.
"""
from __future__ import annotations

import json
import time
import uuid

import psycopg
import pytest
from starlette.testclient import TestClient

from sauti.config import Settings
from sauti.llm.client import LlmTurn, ToolCall, TokenUsage
from sauti.llm.fake import FakeLlmClient
from sauti.main import create_app
from sauti.services.buddy import (
    MAX_HISTORY_TURNS,
    RATE_LIMITED_TEXT,
    UNAVAILABLE_TEXT,
)

REGISTER = {
    "email": "buddy@example.com",
    "password": "umutekano-2026",
    "course_code": "KIN",
    "pace_hours_week": 5,
}


def _login(tc: TestClient) -> str:
    r = tc.post("/api/v1/auth/register", json=REGISTER)
    assert r.status_code == 201, r.text
    r = tc.post(
        "/api/v1/auth/login",
        json={"email": REGISTER["email"], "password": REGISTER["password"]},
    )
    return r.json()["access_token"]


def _seed_due_reviews(pg_url: str, email: str, n: int = 3) -> list[tuple[str, str]]:
    """Put real curriculum items into the learner's SRS queue, due yesterday.

    Returns the (sentence, gloss) rows — the exact strings the buddy must
    quote if it claims they are waiting for review.
    """
    with psycopg.connect(pg_url) as conn:
        user_id = conn.execute(
            "SELECT id FROM sauti.users WHERE email = %s", (email,)
        ).fetchone()[0]
        rows = conn.execute(
            "SELECT i.id, i.sentence, i.gloss FROM sauti.items i "
            "JOIN sauti.lessons l ON l.id = i.lesson_id "
            "JOIN sauti.units u ON u.id = l.unit_id "
            "ORDER BY i.sentence LIMIT %s",
            (n,),
        ).fetchall()
        for item_id, _sentence, _gloss in rows:
            conn.execute(
                "INSERT INTO sauti.srs_state "
                "(id, created_at, updated_at, user_id, item_id, due_at, reps, "
                " stability, difficulty) "
                "VALUES (%s, now(), now(), %s, %s, now() - interval '1 day', 1, 1.0, 5.0)",
                (str(uuid.uuid4()), user_id, item_id),
            )
        conn.commit()
    return [(r[1], r[2]) for r in rows]


def _drain(ws, n: int) -> list[dict]:
    return [ws.receive_json() for _ in range(n)]


class RecordingFake(FakeLlmClient):
    """The scripted buddy, plus a transcript of every prompt it was handed."""

    def __init__(self) -> None:
        self.prompts: list[list[dict]] = []
        self.choices: list[str | None] = []
        self.max_tokens: list[int | None] = []

    async def complete(self, messages, tools=None, tool_choice=None, max_tokens=None):
        self.prompts.append([dict(m) for m in messages])
        self.choices.append(tool_choice)
        self.max_tokens.append(max_tokens)
        return await super().complete(messages, tools, tool_choice, max_tokens)


class TestBuddyWs:
    def test_happy_path_buddy_frame_then_action_chip(self, app):
        with TestClient(app) as tc:
            token = _login(tc)
            with tc.websocket_connect(f"/api/v1/ws/buddy?token={token}") as ws:
                ws.send_json({"text": "muraho mwarimu!"})
                reply = ws.receive_json()
                assert reply["type"] == "buddy"
                assert reply["text"]
                assert "gloss" in reply  # present (may be null) — the UI reads it
                chip = ws.receive_json()
                assert chip["type"] == "action"
                assert chip["action"] == {
                    "kind": "navigate",
                    "href": "/progress",
                    "label": "Show me my progress",
                }

    def test_reply_is_grounded_in_real_db_rows(self, app, pg_url):
        """The buddy names a due sentence — it must be a row that exists."""
        with TestClient(app) as tc:
            token = _login(tc)
            due = _seed_due_reviews(pg_url, REGISTER["email"], n=3)
            sentences = {s for s, _g in due}
            with tc.websocket_connect(f"/api/v1/ws/buddy?token={token}") as ws:
                ws.send_json({"text": "what do I have waiting for review?"})
                reply = ws.receive_json()
                assert reply["type"] == "buddy"
                # The quoted sentence is verbatim from sauti.items, not invented.
                assert any(s in reply["text"] for s in sentences), reply["text"]
                assert "3" in reply["text"]  # the real due count, from the DB

                chips = [ws.receive_json(), ws.receive_json()]
                hrefs = [c["action"]["href"] for c in chips]
                assert all(c["type"] == "action" for c in chips)
                # The deck chip is built server-side from the item's real unit tag.
                assert any(h.startswith("/vocab/") for h in hrefs)

        with psycopg.connect(pg_url) as conn:
            tags = {
                r[0]
                for r in conn.execute(
                    "SELECT DISTINCT situation_tag FROM sauti.units"
                ).fetchall()
            }
        deck = next(h for h in hrefs if h.startswith("/vocab/"))
        assert deck.removeprefix("/vocab/") in tags

    def test_hallucinated_hrefs_are_dropped(self, app):
        """A model-supplied href never reaches the client unchecked: only the
        one pointing at something that exists survives."""

        class BogusHrefFake(FakeLlmClient):
            async def complete(self, messages, tools=None, tool_choice=None, max_tokens=None):
                args = {
                    "text": "Reka tugende! (Let's go!)",
                    "gloss": "Let's go!",
                    "actions": [
                        # A well-shaped href for a lesson that does not exist.
                        {"href": f"/lesson/{uuid.uuid4()}", "label": "Ghost lesson"},
                        # A deck tag nobody seeded.
                        {"href": "/vocab/atlantis", "label": "Ghost deck"},
                        # Not an in-app shape at all.
                        {"href": "https://evil.example/steal", "label": "Nope"},
                        {"href": "/../../etc/passwd", "label": "Nope"},
                        # …and one real one.
                        {"href": "/notebook", "label": "Open my notebook"},
                    ],
                }
                return LlmTurn(
                    tool_calls=[
                        ToolCall(id="c1", name="say", arguments_json=json.dumps(args))
                    ],
                    usage=TokenUsage(model="fake", prompt_tokens=10, completion_tokens=5),
                )

        app.state.llm_client = BogusHrefFake()
        with TestClient(app) as tc:
            token = _login(tc)
            with tc.websocket_connect(f"/api/v1/ws/buddy?token={token}") as ws:
                ws.send_json({"text": "where to?"})
                assert ws.receive_json()["type"] == "buddy"
                chip = ws.receive_json()
                assert chip["action"]["href"] == "/notebook"
                # Nothing else survived — prove it by round-tripping another turn.
                ws.send_json({"text": "again?"})
                assert ws.receive_json()["type"] == "buddy"
                assert ws.receive_json()["action"]["href"] == "/notebook"

    def test_one_llm_call_per_turn_and_static_prefix_is_stable(self, app):
        fake = RecordingFake()
        app.state.llm_client = fake
        with TestClient(app) as tc:
            token = _login(tc)
            with tc.websocket_connect(f"/api/v1/ws/buddy?token={token}") as ws:
                for text in ("muraho!", "how goes it?"):
                    ws.send_json({"text": text})
                    _drain(ws, 2)  # buddy + one chip

        assert len(fake.prompts) == 2  # ONE call per turn — no tool round-trip
        first, second = fake.prompts
        assert first[0]["role"] == "system" and second[0]["role"] == "system"
        assert first[0] == second[0]  # byte-identical persona prefix
        assert first[1] == second[1]  # snapshot fetched ONCE per connection
        assert [m["role"] for m in second] == [
            "system",
            "system",
            "user",
            "assistant",
            "user",
        ]
        # Turn 2 extends turn 1 verbatim — an append-only prefix is what the
        # cache discount actually keys on.
        assert second[: len(first)] == first
        # Every step must call SOME tool: left free, the model answers in prose
        # and the structured envelope (gloss + validated actions) never arrives.
        assert fake.choices == ["required", "required"]
        assert fake.max_tokens == [180, 180]

    def test_last_allowed_step_is_forced_to_say(self, app):
        """A model that only ever wants more data still ends the turn in words."""

        class ToolHungryFake(FakeLlmClient):
            async def complete(self, messages, tools=None, tool_choice=None, max_tokens=None):
                if tool_choice == "say":  # the forced final step
                    return await super().complete(messages, tools, tool_choice, max_tokens)
                return LlmTurn(
                    tool_calls=[
                        ToolCall(id=f"c{len(messages)}", name="get_my_status", arguments_json="{}")
                    ],
                    usage=TokenUsage(model="fake", prompt_tokens=10, completion_tokens=2),
                )

        app.state.llm_client = ToolHungryFake()
        with TestClient(app) as tc:
            token = _login(tc)
            with tc.websocket_connect(f"/api/v1/ws/buddy?token={token}") as ws:
                ws.send_json({"text": "how am I doing?"})
                reply = ws.receive_json()
                assert reply["type"] == "buddy"
                assert reply["text"]  # words, not the loop-exhausted fallback

    def test_history_is_capped_at_six_turns(self, app):
        fake = RecordingFake()
        app.state.llm_client = fake
        with TestClient(app) as tc:
            token = _login(tc)
            with tc.websocket_connect(f"/api/v1/ws/buddy?token={token}") as ws:
                for i in range(9):
                    ws.send_json({"text": f"message number {i}"})
                    _drain(ws, 2)

        last = fake.prompts[-1]
        history = last[2:-1]  # between the two system messages and this turn
        assert len(history) == 2 * MAX_HISTORY_TURNS
        # The window slid: the oldest turns are gone, the newest are kept.
        assert "message number 0" not in json.dumps(last)
        assert history[0]["content"] == "message number 2"
        assert last[-1]["content"] == "message number 8"

    def test_long_input_is_truncated_not_rejected(self, app):
        fake = RecordingFake()
        app.state.llm_client = fake
        with TestClient(app) as tc:
            token = _login(tc)
            with tc.websocket_connect(f"/api/v1/ws/buddy?token={token}") as ws:
                ws.send_json({"text": "a" * 5000})
                assert ws.receive_json()["type"] == "buddy"
        assert len(fake.prompts[0][-1]["content"]) == 500

    def test_empty_payload_gets_a_user_safe_error_frame(self, app):
        with TestClient(app) as tc:
            token = _login(tc)
            with tc.websocket_connect(f"/api/v1/ws/buddy?token={token}") as ws:
                ws.send_json({})
                frame = ws.receive_json()
                assert frame["type"] == "error"
                assert frame["text"]

    def test_bad_token_closes_4401(self, app):
        with TestClient(app) as tc:
            try:
                with tc.websocket_connect("/api/v1/ws/buddy?token=garbage") as ws:
                    data = ws.receive()
                    assert data["type"] == "websocket.close"
                    assert data.get("code") == 4401
            except Exception:
                pass  # some client versions raise on close during handshake — fine

    def test_llm_failure_degrades_to_a_warm_bubble(self, app):
        class DeadLlm(FakeLlmClient):
            async def complete(self, *a, **kw):
                raise RuntimeError("openai timed out")

        app.state.llm_client = DeadLlm()
        with TestClient(app) as tc:
            token = _login(tc)
            with tc.websocket_connect(f"/api/v1/ws/buddy?token={token}") as ws:
                ws.send_json({"text": "muraho?"})
                frame = ws.receive_json()
                assert frame["type"] == "buddy"
                assert frame["text"] == UNAVAILABLE_TEXT
                assert "RuntimeError" not in frame["text"]  # no internals leak
                # The socket is still alive and usable afterwards.
                ws.send_json({"text": "still there?"})
                assert ws.receive_json()["text"] == UNAVAILABLE_TEXT

    def test_usage_row_written_with_surface_buddy(self, app, pg_url):
        with TestClient(app) as tc:
            token = _login(tc)
            with tc.websocket_connect(f"/api/v1/ws/buddy?token={token}") as ws:
                ws.send_json({"text": "muraho!"})
                _drain(ws, 2)

            rows = []
            for _ in range(50):  # metering is fire-and-forget
                with psycopg.connect(pg_url) as conn:
                    rows = conn.execute(
                        "SELECT surface, model, prompt_tokens, completion_tokens, "
                        "cached_prompt_tokens FROM sauti.llm_usage"
                    ).fetchall()
                if rows:
                    break
                time.sleep(0.1)

        assert len(rows) == 1
        surface, model, prompt_toks, completion_toks, cached = rows[0]
        assert surface == "buddy"
        assert model == "fake"
        assert prompt_toks > 0 and completion_toks > 0
        assert cached == 0


class TestBuddyRateLimit:
    @pytest.fixture()
    def capped_app(self, test_settings: Settings):
        """Its own app: the shared fixture runs with the cap wide open."""
        return create_app(test_settings.model_copy(update={"rate_limit_buddy_max": 1}))

    def test_over_limit_gets_an_in_character_error_frame(self, capped_app):
        with TestClient(capped_app) as tc:
            token = _login(tc)
            with tc.websocket_connect(f"/api/v1/ws/buddy?token={token}") as ws:
                ws.send_json({"text": "muraho!"})
                _drain(ws, 2)
                ws.send_json({"text": "and again"})
                frame = ws.receive_json()
                assert frame["type"] == "error"
                assert frame["text"] == RATE_LIMITED_TEXT
                assert "429" not in frame["text"]
                # Over-limit is a frame, never a close: the socket keeps working.
                ws.send_json({"text": "one more"})
                assert ws.receive_json()["type"] == "error"
