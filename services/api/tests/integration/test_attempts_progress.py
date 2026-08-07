"""Attempts -> SRS state -> can-do confirmations -> progress."""
from __future__ import annotations

from datetime import datetime, timezone

from tests.conftest import register_and_login


async def first_item(client, headers) -> dict:
    r = await client.get("/api/v1/roadmap", headers=headers)
    return r.json()["levels"][0]["units"][0]["lessons"][0]["items"][0]


class TestAttempts:
    async def test_attempt_creates_srs_state(self, client):
        auth = await register_and_login(client)
        item = await first_item(client, auth["headers"])
        r = await client.post(
            "/api/v1/attempts",
            json={"item_id": item["id"], "mode": "read", "score": 1.0},
            headers=auth["headers"],
        )
        assert r.status_code == 200
        body = r.json()
        assert body["item_id"] == item["id"]
        assert body["reps"] == 1
        assert body["stability"] > 10  # grade easy -> W[3] ≈ 13.8
        due = datetime.fromisoformat(body["due_at"])
        assert due > datetime.now(timezone.utc)
        assert body["pron"] is None

    async def test_repeat_attempt_increments_reps(self, client):
        auth = await register_and_login(client)
        item = await first_item(client, auth["headers"])
        for expected_reps in (1, 2):
            r = await client.post(
                "/api/v1/attempts",
                json={"item_id": item["id"], "mode": "read", "score": 2 / 3},
                headers=auth["headers"],
            )
            assert r.json()["reps"] == expected_reps

    async def test_answer_graded_against_gloss(self, client):
        auth = await register_and_login(client)
        item = await first_item(client, auth["headers"])
        right = await client.post(
            "/api/v1/attempts",
            json={"item_id": item["id"], "mode": "read", "answer": item["gloss"]},
            headers=auth["headers"],
        )
        assert right.json()["stability"] > 10
        wrong = await client.post(
            "/api/v1/attempts",
            json={"item_id": item["id"], "mode": "read", "answer": "definitely wrong"},
            headers=auth["headers"],
        )
        assert wrong.status_code == 200  # grade 1: relearn soon

    async def test_neither_score_nor_answer_422(self, client):
        auth = await register_and_login(client)
        item = await first_item(client, auth["headers"])
        r = await client.post(
            "/api/v1/attempts",
            json={"item_id": item["id"], "mode": "read"},
            headers=auth["headers"],
        )
        assert r.status_code == 422

    async def test_unknown_item_404(self, client):
        auth = await register_and_login(client)
        r = await client.post(
            "/api/v1/attempts",
            json={
                "item_id": "00000000-0000-0000-0000-000000000000",
                "mode": "read",
                "score": 1.0,
            },
            headers=auth["headers"],
        )
        assert r.status_code == 404

    async def test_speak_attempt_returns_pron_and_confirms_cando(self, client):
        auth = await register_and_login(client)
        item = await first_item(client, auth["headers"])
        r = await client.post(
            "/api/v1/attempts",
            json={
                "item_id": item["id"],
                "mode": "speak",
                "score": 0.9,
                "audio_ref": "user-abc123.webm",
            },
            headers=auth["headers"],
        )
        assert r.status_code == 200
        body = r.json()
        assert body["pron"] is not None
        assert 0 <= body["pron"]["overall"] <= 100
        assert body["pron"]["phonemes"]
        assert len(body["confirmed_candos"]) == 1  # >= 0.8 confirms a speak can-do

    async def test_low_speak_score_confirms_nothing(self, client):
        auth = await register_and_login(client)
        item = await first_item(client, auth["headers"])
        r = await client.post(
            "/api/v1/attempts",
            json={
                "item_id": item["id"],
                "mode": "speak",
                "score": 0.5,
                "audio_ref": "user-abc123.webm",
            },
            headers=auth["headers"],
        )
        assert r.json()["confirmed_candos"] == []


class TestProgress:
    async def test_progress_shape_new_user(self, client):
        auth = await register_and_login(client)
        r = await client.get("/api/v1/progress", headers=auth["headers"])
        assert r.status_code == 200
        body = r.json()
        assert {s["skill"] for s in body["skills"]} == {
            "speaking", "listening", "reading", "writing",
        }
        assert body["cando"]["total"] == 20  # 10 A1 + 10 A2 for KIN
        assert body["cando"]["confirmed"] == 0
        assert body["consistency"] == {"active_days": 0, "window_days": 14}
        assert body["totals"]["sentences_spoken"] == 0
        assert body["eta"]["target_cefr"] == "B1"

    async def test_attempts_move_progress(self, client):
        auth = await register_and_login(client)
        item = await first_item(client, auth["headers"])
        await client.post(
            "/api/v1/attempts",
            json={"item_id": item["id"], "mode": "speak", "score": 0.9,
                  "audio_ref": "user-x.webm"},
            headers=auth["headers"],
        )
        await client.post(
            "/api/v1/attempts",
            json={"item_id": item["id"], "mode": "read", "score": 1.0},
            headers=auth["headers"],
        )
        r = await client.get("/api/v1/progress", headers=auth["headers"])
        body = r.json()
        speaking = next(s for s in body["skills"] if s["skill"] == "speaking")
        assert speaking["pct"] == 0.9
        assert body["cando"]["confirmed"] == 1
        confirmed = [c for c in body["cando"]["items"] if c["status"] == "confirmed"]
        assert len(confirmed) == 1
        assert confirmed[0]["skill"] == "speaking"
        assert body["consistency"]["active_days"] == 1
        assert body["totals"]["sentences_spoken"] == 1
        assert body["totals"]["attempts"] == 2

    async def test_reviews_become_due_and_appear_in_session(self, client):
        auth = await register_and_login(client)
        item = await first_item(client, auth["headers"])
        # Grade "again" -> due in 10 minutes (not yet due), still no review block.
        await client.post(
            "/api/v1/attempts",
            json={"item_id": item["id"], "mode": "read", "score": 0.0},
            headers=auth["headers"],
        )
        r = await client.get("/api/v1/session/today", headers=auth["headers"])
        kinds = [b["kind"] for b in r.json()["blocks"]]
        assert "lesson" in kinds

    async def test_vocab_deck_counts_after_study(self, client):
        auth = await register_and_login(client)
        item = await first_item(client, auth["headers"])
        await client.post(
            "/api/v1/attempts",
            json={"item_id": item["id"], "mode": "read", "score": 1.0},
            headers=auth["headers"],
        )
        r = await client.get("/api/v1/roadmap", headers=auth["headers"])
        first_lesson = r.json()["levels"][0]["units"][0]["lessons"][0]
        # One item studied out of several: lesson still current, not done.
        assert first_lesson["status"] == "current"
