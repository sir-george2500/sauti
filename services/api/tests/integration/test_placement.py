"""Full adaptive placement flow."""
from __future__ import annotations

from sauti.services.placement import MAX_QUESTIONS, MIN_QUESTIONS
from tests.conftest import register_and_login


class TestPlacementFlow:
    async def test_full_flow_places_and_updates_profile(self, client):
        auth = await register_and_login(client)
        r = await client.post("/api/v1/placement/start", headers=auth["headers"])
        assert r.status_code == 200
        body = r.json()
        session_id = body["session_id"]
        q = body["question"]
        assert q["prompt"].startswith("What does")
        assert len(q["options"]) == 4
        assert q["number"] == 1

        answered = 0
        placed = None
        seen_items = {q["item_id"]}
        while answered < MAX_QUESTIONS + 2:
            r = await client.post(
                "/api/v1/placement/answer",
                json={
                    "session_id": session_id,
                    "item_id": q["item_id"],
                    "answer": q["options"][0],
                },
                headers=auth["headers"],
            )
            assert r.status_code == 200, r.text
            body = r.json()
            answered += 1
            if body.get("placed_level"):
                placed = body["placed_level"]
                assert body["result"] == placed
                break
            q = body["question"]
            assert q["item_id"] not in seen_items  # never re-serve an item
            seen_items.add(q["item_id"])

        assert placed in ("A1", "A2")  # clamped to seeded levels
        assert MIN_QUESTIONS <= answered <= MAX_QUESTIONS

        r = await client.get("/api/v1/me", headers=auth["headers"])
        assert r.json()["profile"]["placed_level"] == placed

    async def test_all_correct_places_at_top_seeded_level(self, client):
        auth = await register_and_login(client)
        r = await client.post("/api/v1/placement/start", headers=auth["headers"])
        session_id = r.json()["session_id"]
        q = r.json()["question"]

        # Cheat: look the correct gloss up in the roadmap item payloads.
        roadmap = (await client.get("/api/v1/roadmap", headers=auth["headers"])).json()
        gloss_by_id = {
            i["id"]: i["gloss"]
            for lvl in roadmap["levels"]
            for u in lvl["units"]
            for les in u["lessons"]
            for i in les["items"]
        }
        for _ in range(MAX_QUESTIONS + 2):
            r = await client.post(
                "/api/v1/placement/answer",
                json={
                    "session_id": session_id,
                    "item_id": q["item_id"],
                    "answer": gloss_by_id[q["item_id"]],
                },
                headers=auth["headers"],
            )
            body = r.json()
            if body.get("placed_level"):
                assert body["placed_level"] == "A2"  # top of the seeded course
                return
            q = body["question"]
        raise AssertionError("placement never finished")

    async def test_out_of_order_answer_409(self, client):
        auth = await register_and_login(client)
        r = await client.post("/api/v1/placement/start", headers=auth["headers"])
        session_id = r.json()["session_id"]
        r = await client.post(
            "/api/v1/placement/answer",
            json={
                "session_id": session_id,
                "item_id": "00000000-0000-0000-0000-000000000001",
                "answer": "whatever",
            },
            headers=auth["headers"],
        )
        assert r.status_code == 409

    async def test_finished_session_rejects_more_answers(self, client):
        auth = await register_and_login(client)
        r = await client.post("/api/v1/placement/start", headers=auth["headers"])
        session_id = r.json()["session_id"]
        q = r.json()["question"]
        last_item = q["item_id"]
        for _ in range(MAX_QUESTIONS + 2):
            r = await client.post(
                "/api/v1/placement/answer",
                json={"session_id": session_id, "item_id": q["item_id"],
                      "answer": q["options"][0]},
                headers=auth["headers"],
            )
            body = r.json()
            if body.get("placed_level"):
                break
            last_item = body["question"]["item_id"]
            q = body["question"]
        r = await client.post(
            "/api/v1/placement/answer",
            json={"session_id": session_id, "item_id": last_item, "answer": "x"},
            headers=auth["headers"],
        )
        assert r.status_code == 409

    async def test_other_users_session_404(self, client):
        auth1 = await register_and_login(client, email="a@example.com")
        auth2 = await register_and_login(client, email="b@example.com")
        r = await client.post("/api/v1/placement/start", headers=auth1["headers"])
        sid = r.json()["session_id"]
        item = r.json()["question"]["item_id"]
        r = await client.post(
            "/api/v1/placement/answer",
            json={"session_id": sid, "item_id": item, "answer": "x"},
            headers=auth2["headers"],
        )
        assert r.status_code == 404
