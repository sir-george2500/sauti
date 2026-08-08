"""Ikaye (word notebook) API + the daily-goal profile patch."""
from __future__ import annotations

import pytest

from tests.conftest import register_and_login


async def _first_item(client, headers) -> dict:
    r = await client.get("/api/v1/roadmap", headers=headers)
    assert r.status_code == 200
    for level in r.json()["levels"]:
        for unit in level["units"]:
            for lesson in unit["lessons"]:
                if lesson["items"]:
                    return lesson["items"][0]
    raise AssertionError("seeded roadmap has no items")


class TestNotebookCrud:
    async def test_free_form_lifecycle(self, client):
        auth = await register_and_login(client)
        h = auth["headers"]

        r = await client.get("/api/v1/notebook", headers=h)
        assert r.status_code == 200 and r.json() == []

        r = await client.post(
            "/api/v1/notebook",
            headers=h,
            json={"text": "Urakoze", "gloss": "Thank you", "note": "heard at the market"},
        )
        assert r.status_code == 201, r.text
        entry = r.json()
        assert entry["text"] == "Urakoze"
        assert entry["gloss"] == "Thank you"
        assert entry["note"] == "heard at the market"
        assert entry["item_id"] is None
        assert entry["audio_url"] is None

        # PATCH the note only — text/gloss untouched.
        r = await client.patch(
            f"/api/v1/notebook/{entry['id']}",
            headers=h,
            json={"note": "polite form of thanks"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["note"] == "polite form of thanks"
        assert r.json()["text"] == "Urakoze"

        r = await client.delete(f"/api/v1/notebook/{entry['id']}", headers=h)
        assert r.status_code == 204
        r = await client.get("/api/v1/notebook", headers=h)
        assert r.json() == []

    async def test_entries_newest_first(self, client):
        auth = await register_and_login(client)
        h = auth["headers"]
        for text in ("rimwe", "kabiri", "gatatu"):
            r = await client.post("/api/v1/notebook", headers=h, json={"text": text})
            assert r.status_code == 201
        r = await client.get("/api/v1/notebook", headers=h)
        assert [e["text"] for e in r.json()] == ["gatatu", "kabiri", "rimwe"]

    async def test_post_requires_text_or_item(self, client):
        auth = await register_and_login(client)
        r = await client.post(
            "/api/v1/notebook", headers=auth["headers"], json={"note": "just a note"}
        )
        assert r.status_code == 422

    async def test_blank_text_rejected(self, client):
        auth = await register_and_login(client)
        r = await client.post(
            "/api/v1/notebook", headers=auth["headers"], json={"text": "   "}
        )
        assert r.status_code == 422

    async def test_patch_cannot_blank_text(self, client):
        auth = await register_and_login(client)
        h = auth["headers"]
        r = await client.post("/api/v1/notebook", headers=h, json={"text": "Amakuru?"})
        entry_id = r.json()["id"]
        r = await client.patch(
            f"/api/v1/notebook/{entry_id}", headers=h, json={"text": "  "}
        )
        assert r.status_code == 422
        r = await client.get("/api/v1/notebook", headers=h)
        assert r.json()[0]["text"] == "Amakuru?"


class TestItemSnapshot:
    async def test_item_id_snapshots_sentence_and_gloss(self, client):
        auth = await register_and_login(client)
        h = auth["headers"]
        item = await _first_item(client, h)

        r = await client.post("/api/v1/notebook", headers=h, json={"item_id": item["id"]})
        assert r.status_code == 201, r.text
        entry = r.json()
        assert entry["item_id"] == item["id"]
        assert entry["text"] == item["sentence"]
        assert entry["gloss"] == item["gloss"]
        assert entry["item_sentence"] == item["sentence"]

    async def test_explicit_text_wins_over_snapshot(self, client):
        auth = await register_and_login(client)
        h = auth["headers"]
        item = await _first_item(client, h)
        r = await client.post(
            "/api/v1/notebook",
            headers=h,
            json={"item_id": item["id"], "text": "my own phrasing"},
        )
        assert r.status_code == 201
        assert r.json()["text"] == "my own phrasing"
        assert r.json()["gloss"] == item["gloss"]  # gloss still snapshotted

    async def test_unknown_item_404(self, client):
        auth = await register_and_login(client)
        r = await client.post(
            "/api/v1/notebook",
            headers=auth["headers"],
            json={"item_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert r.status_code == 404

    async def test_item_linked_entry_carries_cached_audio_url(self, client, pg_url):
        import psycopg

        from sauti.speech.cache import cache_key

        auth = await register_and_login(client)
        h = auth["headers"]
        item = await _first_item(client, h)

        # Cache the item's TTS with the exact key derivation the cache uses.
        key = cache_key(str(item.get("voice_id") or ""), item["sentence"])
        url = f"https://res.cloudinary.com/sauti/video/upload/sauti/tts/{key}.wav"
        with psycopg.connect(pg_url) as conn:
            conn.execute(
                "INSERT INTO sauti.tts_cache (id, key, voice, url, created_at, updated_at) "
                "VALUES (gen_random_uuid(), %s, %s, %s, now(), now())",
                (key, str(item.get("voice_id") or ""), url),
            )
            conn.commit()

        r = await client.post("/api/v1/notebook", headers=h, json={"item_id": item["id"]})
        assert r.status_code == 201
        assert r.json()["audio_url"] == url

        r = await client.get("/api/v1/notebook", headers=h)
        assert r.json()[0]["audio_url"] == url


class TestOwnership:
    async def test_foreign_entries_are_invisible_and_untouchable(self, client):
        owner = await register_and_login(client, email="owner@example.com")
        r = await client.post(
            "/api/v1/notebook", headers=owner["headers"], json={"text": "Ndabizi"}
        )
        entry_id = r.json()["id"]

        other = await register_and_login(client, email="other@example.com")
        oh = other["headers"]

        r = await client.get("/api/v1/notebook", headers=oh)
        assert r.json() == []
        r = await client.patch(
            f"/api/v1/notebook/{entry_id}", headers=oh, json={"note": "mine now"}
        )
        assert r.status_code == 404
        r = await client.delete(f"/api/v1/notebook/{entry_id}", headers=oh)
        assert r.status_code == 404

        # Owner's entry is untouched.
        r = await client.get("/api/v1/notebook", headers=owner["headers"])
        assert len(r.json()) == 1 and r.json()[0]["note"] is None

    async def test_requires_auth(self, client):
        r = await client.get("/api/v1/notebook")
        assert r.status_code == 401


class TestDailyGoal:
    async def test_me_defaults_to_25(self, client):
        auth = await register_and_login(client)
        r = await client.get("/api/v1/me", headers=auth["headers"])
        assert r.status_code == 200
        assert r.json()["profile"]["daily_goal_minutes"] == 25

    async def test_patch_updates_goal(self, client):
        auth = await register_and_login(client)
        h = auth["headers"]
        r = await client.patch(
            "/api/v1/me/profile", headers=h, json={"daily_goal_minutes": 15}
        )
        assert r.status_code == 200, r.text
        assert r.json()["daily_goal_minutes"] == 15
        r = await client.get("/api/v1/me", headers=h)
        assert r.json()["profile"]["daily_goal_minutes"] == 15

    @pytest.mark.parametrize("minutes", [4, 121, 0, -5])
    async def test_patch_validates_range(self, client, minutes):
        auth = await register_and_login(client)
        r = await client.patch(
            "/api/v1/me/profile",
            headers=auth["headers"],
            json={"daily_goal_minutes": minutes},
        )
        assert r.status_code == 422

    async def test_patch_requires_auth(self, client):
        r = await client.patch("/api/v1/me/profile", json={"daily_goal_minutes": 15})
        assert r.status_code == 401
