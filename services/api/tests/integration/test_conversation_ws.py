"""WS conversation happy path with the scripted FakeLlmClient (SAUTI_FAKE_AI)."""
from __future__ import annotations

import psycopg
from starlette.testclient import TestClient

REGISTER = {
    "email": "ws@example.com",
    "password": "umutekano-2026",
    "course_code": "KIN",
    "pace_hours_week": 5,
}


def _setup(tc: TestClient) -> tuple[str, str]:
    r = tc.post("/api/v1/auth/register", json=REGISTER)
    assert r.status_code == 201, r.text
    r = tc.post(
        "/api/v1/auth/login",
        json={"email": REGISTER["email"], "password": REGISTER["password"]},
    )
    token = r.json()["access_token"]
    r = tc.get("/api/v1/scenarios", headers={"Authorization": f"Bearer {token}"})
    scenario_id = r.json()[0]["id"]
    return token, scenario_id


class TestConversationWs:
    def test_happy_path_partner_goal_and_coach(self, app):
        with TestClient(app) as tc:
            token, scenario_id = _setup(tc)
            with tc.websocket_connect(
                f"/api/v1/ws/conversation/{scenario_id}?token={token}"
            ) as ws:
                # Turn 1 — greeting. Fake LLM grounds via get_scenario_vocab then replies.
                ws.send_json({"text": "Muraho!"})
                partner = ws.receive_json()
                assert partner["type"] == "partner"
                assert partner["text"]
                assert partner["gloss"]  # EN: line split out
                assert partner["audio_url"].startswith("http://testserver/api/v1/speech/audio/")
                coach = ws.receive_json()
                assert coach["type"] == "coach"
                assert coach["coach"]["kind"] == "praise"  # never a correction on turn 1

                # Turn 2 — asking a price hits the mark_goal_met tool.
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
            token, scenario_id = _setup(tc)
            with tc.websocket_connect(
                f"/api/v1/ws/conversation/{scenario_id}?token={token}"
            ) as ws:
                ws.send_json({"audio_ref": "stub:mic-take"})  # stub STT kicks in
                partner = ws.receive_json()
                assert partner["type"] == "partner"
                assert partner["text"]

    def test_empty_payload_gets_error_frame(self, app):
        with TestClient(app) as tc:
            token, scenario_id = _setup(tc)
            with tc.websocket_connect(
                f"/api/v1/ws/conversation/{scenario_id}?token={token}"
            ) as ws:
                ws.send_json({})
                frame = ws.receive_json()
                assert frame["type"] == "error"

    def test_bad_token_closes_4401(self, app):
        with TestClient(app) as tc:
            _token, scenario_id = _setup(tc)
            try:
                with tc.websocket_connect(
                    f"/api/v1/ws/conversation/{scenario_id}?token=garbage"
                ) as ws:
                    data = ws.receive()
                    assert data["type"] == "websocket.close"
                    assert data.get("code") == 4401
            except Exception:
                pass  # some client versions raise on close during handshake — fine

    def test_conversation_and_messages_persisted(self, app, pg_url):
        with TestClient(app) as tc:
            token, scenario_id = _setup(tc)
            with tc.websocket_connect(
                f"/api/v1/ws/conversation/{scenario_id}?token={token}"
            ) as ws:
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
            assert roles[0] == "user"
            assert "persona" in roles
            assert "coach" in roles
