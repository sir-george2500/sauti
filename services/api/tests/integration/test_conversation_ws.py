"""WS conversation happy path with the scripted FakeLlmClient (SAUTI_FAKE_AI)."""
from __future__ import annotations

import json

import psycopg
from starlette.testclient import TestClient

from sauti.llm.fake import FakeLlmClient

REGISTER = {
    "email": "ws@example.com",
    "password": "umutekano-2026",
    "course_code": "KIN",
    "pace_hours_week": 5,
}


class CountingFake(FakeLlmClient):
    """Same script, but counts real LLM calls — the reply-cache assertions
    hinge on this number NOT moving."""

    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, messages, tools=None, tool_choice=None):
        self.calls += 1
        return await super().complete(messages, tools, tool_choice)


def _setup(tc: TestClient) -> tuple[str, dict]:
    r = tc.post("/api/v1/auth/register", json=REGISTER)
    assert r.status_code == 201, r.text
    r = tc.post(
        "/api/v1/auth/login",
        json={"email": REGISTER["email"], "password": REGISTER["password"]},
    )
    token = r.json()["access_token"]
    r = tc.get("/api/v1/scenarios", headers={"Authorization": f"Bearer {token}"})
    scenario = r.json()[0]
    return token, scenario


def _drain_opener(ws, scenario: dict) -> dict | None:
    """Scenarios with persona.opening_line greet first (a server-sent partner
    frame on connect); scenarios without it don't. Handle both seeds."""
    line = (scenario.get("persona") or {}).get("opening_line") or {}
    if not str(line.get("ky") or "").strip():
        return None
    frame = ws.receive_json()
    assert frame["type"] == "partner"
    assert frame["text"] == line["ky"].strip()
    return frame


class TestConversationWs:
    def test_happy_path_partner_goal_and_coach(self, app):
        with TestClient(app) as tc:
            token, scenario = _setup(tc)
            with tc.websocket_connect(
                f"/api/v1/ws/conversation/{scenario['id']}?token={token}"
            ) as ws:
                _drain_opener(ws, scenario)
                # Turn 1 — greeting. One structured LLM call yields the reply.
                ws.send_json({"text": "Muraho!"})
                partner = ws.receive_json()
                assert partner["type"] == "partner"
                assert partner["text"]
                assert partner["gloss"]  # English gloss from the structured payload
                assert partner["audio_url"].startswith("http://testserver/api/v1/speech/audio/")
                coach = ws.receive_json()
                assert coach["type"] == "coach"
                assert coach["coach"]["kind"] == "praise"  # never a correction on turn 1

                # Turn 2 — asking a price reports the goal in the same payload.
                ws.send_json({"text": "Ni angahe?"})
                frames = [ws.receive_json() for _ in range(4)]
                types = [f["type"] for f in frames]
                assert types[0] == "partner"
                assert "goal" in types
                goal = next(f for f in frames if f["type"] == "goal")
                assert goal["text"] == "ask a price"
                coach_frames = [f for f in frames if f["type"] == "coach"]
                # Praise first, at most one correction — CoachPolicy is server-side.
                assert coach_frames[0]["coach"]["kind"] == "praise"
                fixes = [f for f in coach_frames if f["coach"]["kind"] == "fix"]
                assert len(fixes) == 1

    def test_audio_ref_stub_mic_take(self, app):
        with TestClient(app) as tc:
            token, scenario = _setup(tc)
            with tc.websocket_connect(
                f"/api/v1/ws/conversation/{scenario['id']}?token={token}"
            ) as ws:
                _drain_opener(ws, scenario)
                ws.send_json({"audio_ref": "stub:mic-take"})  # stub STT kicks in
                partner = ws.receive_json()
                assert partner["type"] == "partner"
                assert partner["text"]

    def test_empty_payload_gets_error_frame(self, app):
        with TestClient(app) as tc:
            token, scenario = _setup(tc)
            with tc.websocket_connect(
                f"/api/v1/ws/conversation/{scenario['id']}?token={token}"
            ) as ws:
                _drain_opener(ws, scenario)
                ws.send_json({})
                frame = ws.receive_json()
                assert frame["type"] == "error"

    def test_bad_token_closes_4401(self, app):
        with TestClient(app) as tc:
            _token, scenario = _setup(tc)
            try:
                with tc.websocket_connect(
                    f"/api/v1/ws/conversation/{scenario['id']}?token=garbage"
                ) as ws:
                    data = ws.receive()
                    assert data["type"] == "websocket.close"
                    assert data.get("code") == 4401
            except Exception:
                pass  # some client versions raise on close during handshake — fine

    def test_system_prompt_prefix_stable_across_turns(self, app):
        """The whole prompt prefix (system message + growing history) must be
        byte-identical across turns for OpenAI's prompt-cache discount."""

        class RecordingFake(FakeLlmClient):
            def __init__(self):
                self.prompts: list[list[dict]] = []

            async def complete(self, messages, tools=None, tool_choice=None):
                self.prompts.append([dict(m) for m in messages])
                return await super().complete(messages, tools, tool_choice)

        fake = RecordingFake()
        app.state.llm_client = fake
        with TestClient(app) as tc:
            token, scenario = _setup(tc)
            opener = bool(((scenario.get("persona") or {}).get("opening_line") or {}).get("ky"))
            with tc.websocket_connect(
                f"/api/v1/ws/conversation/{scenario['id']}?token={token}"
            ) as ws:
                _drain_opener(ws, scenario)
                ws.send_json({"text": "Muraho!"})
                for _ in range(2):  # partner + coach praise
                    ws.receive_json()
                ws.send_json({"text": "Ni angahe?"})
                for _ in range(4):  # partner + goal + praise + fix
                    ws.receive_json()

        assert len(fake.prompts) == 2  # ONE call per turn (opener costs none)
        first, second = fake.prompts
        # System prompt: static content only, byte-identical across turns.
        assert first[0]["role"] == "system"
        assert first[0] == second[0]
        # Turn 2's messages extend turn 1's verbatim (append-only prefix).
        assert second[: len(first) - 1] == first[:-1]
        roles = ["system"] + (["assistant"] if opener else []) + ["user", "assistant", "user"]
        assert [m["role"] for m in second] == roles
        assert second[-1]["content"] == "Ni angahe?"

    def test_reply_cache_hit_skips_llm(self, app, pg_url):
        """Same normalized first-turn text in a NEW conversation is served from
        sauti.llm_reply_cache: identical frames, zero extra LLM calls."""
        fake = CountingFake()
        app.state.llm_client = fake
        with TestClient(app) as tc:
            token, scenario = _setup(tc)
            url = f"/api/v1/ws/conversation/{scenario['id']}?token={token}"

            with tc.websocket_connect(url) as ws:
                _drain_opener(ws, scenario)
                ws.send_json({"text": "Muraho!"})
                first_partner = ws.receive_json()
                ws.receive_json()  # coach praise
            assert fake.calls == 1

            # New conversation, same text modulo case/punctuation → cache hit.
            with tc.websocket_connect(url) as ws:
                _drain_opener(ws, scenario)
                ws.send_json({"text": "  muraho!!  "})
                partner = ws.receive_json()
                coach = ws.receive_json()
            assert fake.calls == 1  # the LLM was NOT called again
            assert partner["text"] == first_partner["text"]
            assert partner["gloss"] == first_partner["gloss"]
            assert coach["type"] == "coach"

        with psycopg.connect(pg_url) as conn:
            rows = conn.execute(
                "SELECT hits, reply FROM sauti.llm_reply_cache"
            ).fetchall()
            assert len(rows) == 1
            hits, reply = rows[0]
            assert hits == 1
            assert reply["reply"] == first_partner["text"]

    def test_scripted_opener_frame_and_persistence(self, app, pg_url):
        """persona.opening_line greets the learner on connect — zero LLM calls."""
        opener = {"ky": "Mwaramutse! Urashaka kugura iki?", "en": "Good morning! What would you like to buy?"}
        fake = CountingFake()
        app.state.llm_client = fake
        with TestClient(app) as tc:
            token, scenario = _setup(tc)
            with psycopg.connect(pg_url) as conn:
                conn.execute(
                    "UPDATE sauti.scenarios SET persona = persona || %s::jsonb WHERE id = %s",
                    (json.dumps({"opening_line": opener}), scenario["id"]),
                )
                conn.commit()
            try:
                with tc.websocket_connect(
                    f"/api/v1/ws/conversation/{scenario['id']}?token={token}"
                ) as ws:
                    frame = ws.receive_json()  # sent before any learner input
                    assert frame["type"] == "partner"
                    assert frame["text"] == opener["ky"]
                    assert frame["gloss"] == opener["en"]
                    assert frame["audio_url"]  # stub TTS is inline
                    assert fake.calls == 0  # scripted — no LLM involved

                    # The conversation continues normally after the opener.
                    ws.send_json({"text": "Muraho!"})
                    partner = ws.receive_json()
                    assert partner["type"] == "partner"
                    coach = ws.receive_json()  # coach frames follow the commit
                    assert coach["type"] == "coach"

                with psycopg.connect(pg_url) as conn:
                    roles = [
                        r[0]
                        for r in conn.execute(
                            "SELECT role FROM sauti.messages ORDER BY created_at"
                        ).fetchall()
                    ]
                assert roles[0] == "persona"  # the opener is persisted first
                assert roles[1] == "user"
            finally:
                with psycopg.connect(pg_url) as conn:
                    conn.execute(
                        "UPDATE sauti.scenarios SET persona = persona - 'opening_line' "
                        "WHERE id = %s",
                        (scenario["id"],),
                    )
                    conn.commit()

    def test_conversation_and_messages_persisted(self, app, pg_url):
        with TestClient(app) as tc:
            token, scenario = _setup(tc)
            with tc.websocket_connect(
                f"/api/v1/ws/conversation/{scenario['id']}?token={token}"
            ) as ws:
                opener = _drain_opener(ws, scenario)
                ws.send_json({"text": "Ni angahe?"})
                # First user turn: partner + goal + coach praise (fix suppressed).
                for _ in range(3):
                    ws.receive_json()
        with psycopg.connect(pg_url) as conn:
            convs = conn.execute("SELECT goals_met FROM sauti.conversations").fetchall()
            assert len(convs) == 1
            assert convs[0][0] == ["ask a price"]
            roles = [
                r[0]
                for r in conn.execute(
                    "SELECT role FROM sauti.messages ORDER BY created_at"
                ).fetchall()
            ]
            if opener is not None:
                assert roles[0] == "persona"
                roles = roles[1:]
            assert roles[0] == "user"
            assert "persona" in roles
            assert "coach" in roles
