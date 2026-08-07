"""GET /progress/recordings — the "Hear yourself change" archive.

Recordings derive from speak attempts that kept their audio_ref; the endpoint
resolves each ref to the same public route the upload flow serves audio from.
"""
from __future__ import annotations

import psycopg

from tests.conftest import register_and_login


async def lesson_items(client, headers, n: int = 2) -> list[dict]:
    r = await client.get("/api/v1/roadmap", headers=headers)
    return r.json()["levels"][0]["units"][0]["lessons"][0]["items"][:n]


async def post_speak(client, headers, item_id: str, audio_ref: str | None, score: float = 0.9):
    body = {"item_id": item_id, "mode": "speak", "score": score}
    if audio_ref is not None:
        body["audio_ref"] = audio_ref
    r = await client.post("/api/v1/attempts", json=body, headers=headers)
    assert r.status_code == 200, r.text


class TestRecordingsArchive:
    async def test_empty_for_new_user(self, client):
        auth = await register_and_login(client)
        r = await client.get("/api/v1/progress/recordings", headers=auth["headers"])
        assert r.status_code == 200
        assert r.json() == []

    async def test_lists_only_speak_attempts_with_audio(self, client):
        auth = await register_and_login(client)
        items = await lesson_items(client, auth["headers"])

        # Noise: a read attempt and a speak attempt without kept audio.
        r = await client.post(
            "/api/v1/attempts",
            json={"item_id": items[0]["id"], "mode": "read", "score": 1.0},
            headers=auth["headers"],
        )
        assert r.status_code == 200
        await post_speak(client, auth["headers"], items[0]["id"], audio_ref=None)

        # Two kept takes, chronological.
        await post_speak(client, auth["headers"], items[0]["id"], "user-take1.webm", 0.7)
        await post_speak(client, auth["headers"], items[1]["id"], "user-take2.webm", 0.9)

        r = await client.get("/api/v1/progress/recordings", headers=auth["headers"])
        assert r.status_code == 200
        recs = r.json()
        assert len(recs) == 2
        first, latest = recs
        assert first["item_sentence"] == items[0]["sentence"]
        assert latest["item_sentence"] == items[1]["sentence"]
        assert first["ts"] <= latest["ts"]
        assert first["day_number"] == 1
        assert latest["day_number"] == 1  # same day
        assert first["score"] == 0.7
        assert first["audio_url"] == "http://testserver/api/v1/speech/audio/user-take1.webm"
        assert latest["audio_url"].endswith("/api/v1/speech/audio/user-take2.webm")

    async def test_day_numbers_count_from_first_recording(self, client, pg_url):
        auth = await register_and_login(client)
        items = await lesson_items(client, auth["headers"])
        await post_speak(client, auth["headers"], items[0]["id"], "user-week1.webm")
        await post_speak(client, auth["headers"], items[0]["id"], "user-day34.webm")

        # Time machine: the first take happened 33 days ago (design: "Week 1"
        # vs "Day 34 — same phrase, 33 days apart").
        with psycopg.connect(pg_url) as conn:
            conn.execute(
                "UPDATE sauti.attempts SET ts = ts - interval '33 days' "
                "WHERE audio_ref = 'user-week1.webm'"
            )
            conn.commit()

        r = await client.get("/api/v1/progress/recordings", headers=auth["headers"])
        recs = r.json()
        assert [rec["day_number"] for rec in recs] == [1, 34]
        assert recs[0]["audio_url"].endswith("user-week1.webm")
        assert recs[1]["audio_url"].endswith("user-day34.webm")
