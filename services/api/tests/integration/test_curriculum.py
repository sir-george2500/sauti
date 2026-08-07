"""Courses, roadmap (embedded lessons), vocab decks, scenarios."""
from __future__ import annotations

from tests.conftest import register_and_login


class TestCourses:
    async def test_three_courses_with_availability(self, client):
        r = await client.get("/api/v1/courses")
        assert r.status_code == 200
        by_code = {c["code"]: c for c in r.json()}
        assert set(by_code) == {"KIN", "SWA", "FRA"}
        assert by_code["KIN"]["available"] is True
        assert by_code["SWA"]["available"] is False  # skeleton
        assert by_code["FRA"]["available"] is False  # skeleton


class TestRoadmap:
    async def test_shape_and_embedded_lesson_payloads(self, client):
        auth = await register_and_login(client)
        r = await client.get("/api/v1/roadmap", headers=auth["headers"])
        assert r.status_code == 200
        body = r.json()
        assert body["course_code"] == "KIN"
        assert [lvl["cefr"] for lvl in body["levels"]] == ["A1", "A2"]

        a1 = body["levels"][0]
        assert a1["status"] == "current"
        assert [u["title"] for u in a1["units"]] == [
            "Greetings & people",
            "Family & home",
            "Numbers & time",
        ]
        for unit in a1["units"]:
            assert 3 <= len(unit["lessons"]) <= 5

        first = a1["units"][0]["lessons"][0]
        assert first["status"] == "current"
        # Embedded lesson payload (there is no GET /lessons/{id}).
        assert "umu-" in first["grammar_md"] or "mu-" in first["grammar_md"]
        assert first["culture_note"]
        assert 6 <= len(first["items"]) <= 12
        item = first["items"][0]
        assert item["sentence"] and item["gloss"]
        assert item["phoneme_ref"]["syllables"]

        qc = first["quick_check"]
        assert qc["question"]
        assert len(qc["options"]) == 4
        assert sum(1 for o in qc["options"] if o["correct"]) == 1

        assert body["current"]["cefr"] == "A1"
        assert body["current"]["unit_title"] == "Greetings & people"
        assert body["current"]["lesson_id"] == first["id"]
        assert body["eta"]["target_cefr"] == "B1"  # after finishing seeded A1+A2
        assert body["eta"]["pace_hours_week"] == 5

    async def test_design_anchor_content_present(self, client):
        auth = await register_and_login(client)
        r = await client.get("/api/v1/roadmap", headers=auth["headers"])
        text = r.text
        assert "Amakuru yawe?" in text
        assert "Umwana" in text and "abana" in text
        assert "Buhoro buhoro ni rwo rugendo" in text
        assert "Gabanya gato" in text  # market bargaining

    async def test_quick_check_deterministic(self, client):
        auth = await register_and_login(client)
        r1 = await client.get("/api/v1/roadmap", headers=auth["headers"])
        r2 = await client.get("/api/v1/roadmap", headers=auth["headers"])
        assert r1.json() == r2.json()


class TestVocabDecks:
    async def test_decks_grouped_by_situation(self, client):
        auth = await register_and_login(client)
        r = await client.get("/api/v1/vocab/decks", headers=auth["headers"])
        assert r.status_code == 200
        body = r.json()
        tags = [d["tag"] for d in body["decks"]]
        assert tags == ["greetings", "family", "numbers", "transport", "market", "food"]
        deck = body["decks"][0]
        assert deck["word_count"] > 0
        assert deck["due_count"] == 0
        assert deck["mastery"] == 0.0
        assert deck["sample"]["sentence"]
        assert body["total_due"] == 0

    async def test_deck_detail_and_404(self, client):
        auth = await register_and_login(client)
        r = await client.get("/api/v1/vocab/decks/market", headers=auth["headers"])
        assert r.status_code == 200
        body = r.json()
        assert body["tag"] == "market"
        assert any("angahe" in i["sentence"].lower() for i in body["items"])
        r = await client.get("/api/v1/vocab/decks/nope", headers=auth["headers"])
        assert r.status_code == 404


class TestScenarios:
    async def test_kimironko_scenario_listed(self, client):
        auth = await register_and_login(client)
        r = await client.get("/api/v1/scenarios", headers=auth["headers"])
        assert r.status_code == 200
        scenarios = r.json()
        assert len(scenarios) == 1
        s = scenarios[0]
        assert s["title"] == "Kimironko market run"
        assert s["persona"]["name"] == "Mukamana"
        assert s["persona"]["role"] == "vegetable vendor"
        assert s["min_cefr"] == "A1"
        assert s["umuco_tip"]
        assert len(s["goals"]) == 4
        assert s["voice_id"]


class TestSessionToday:
    async def test_new_user_plan(self, client):
        auth = await register_and_login(client)
        r = await client.get("/api/v1/session/today", headers=auth["headers"])
        assert r.status_code == 200
        plan = r.json()
        kinds = [b["kind"] for b in plan["blocks"]]
        assert kinds == ["lesson", "speak"]  # nothing due yet
        assert plan["total_min"] == 25
        lesson_block = plan["blocks"][0]
        assert lesson_block["tag"] == "GREETINGS"
        speak_block = plan["blocks"][1]
        assert "speaking" in speak_block["sub"]  # new learner: weakest = speak
