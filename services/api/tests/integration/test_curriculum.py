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


class TestItemAudioUrls:
    """Item payloads carry the cached TTS URL directly — no GET /tts round trip
    before play. Uncached items are null (client falls back to /tts)."""

    @staticmethod
    def _cache_audio(pg_url: str, sentences: list[str]) -> dict[str, str]:
        """Insert tts_cache rows for the given KIN item sentences, using the
        exact key derivation the speech cache uses. Returns sentence -> url."""
        import psycopg

        from sauti.speech.cache import cache_key

        urls: dict[str, str] = {}
        with psycopg.connect(pg_url) as conn:
            for sentence in sentences:
                row = conn.execute(
                    "SELECT id, voice_id FROM sauti.items WHERE sentence = %s",
                    (sentence,),
                ).fetchone()
                assert row is not None, f"seeded item not found: {sentence}"
                key = cache_key(str(row[1] or ""), sentence)
                url = f"https://res.cloudinary.com/sauti/video/upload/sauti/tts/{key}.wav"
                conn.execute(
                    "INSERT INTO sauti.tts_cache (id, key, voice, url, created_at, updated_at) "
                    "VALUES (gen_random_uuid(), %s, %s, %s, now(), now())",
                    (key, str(row[1] or ""), url),
                )
                urls[sentence] = url
            conn.commit()
        return urls

    async def test_roadmap_items_carry_cached_audio_urls(self, client, pg_url):
        urls = self._cache_audio(pg_url, ["Mwaramutse!", "Ni angahe?"])
        auth = await register_and_login(client)
        r = await client.get("/api/v1/roadmap", headers=auth["headers"])
        assert r.status_code == 200
        items = {
            i["sentence"]: i
            for lvl in r.json()["levels"]
            for u in lvl["units"]
            for les in u["lessons"]
            for i in les["items"]
        }
        assert items["Mwaramutse!"]["audio_url"] == urls["Mwaramutse!"]
        assert items["Ni angahe?"]["audio_url"] == urls["Ni angahe?"]
        # Uncached -> null, client falls back to GET /tts/{item_id}.
        assert items["Mwiriwe neza."]["audio_url"] is None

    async def test_vocab_deck_items_carry_cached_audio_urls(self, client, pg_url):
        urls = self._cache_audio(pg_url, ["Ni angahe?"])
        auth = await register_and_login(client)
        r = await client.get("/api/v1/vocab/decks/market", headers=auth["headers"])
        assert r.status_code == 200
        deck_items = {i["sentence"]: i for i in r.json()["items"]}
        assert deck_items["Ni angahe?"]["audio_url"] == urls["Ni angahe?"]
        assert deck_items["Gabanya gato."]["audio_url"] is None

    async def test_roadmap_resolves_audio_with_one_bulk_query(self, app, client, pg_url):
        """The whole roadmap (all embedded items) costs exactly ONE tts_cache
        query — the dev DB is ~380 ms/round-trip, so N+1 here is the 30 s bug."""
        from sqlalchemy import event

        self._cache_audio(pg_url, ["Mwaramutse!"])
        auth = await register_and_login(client)
        statements: list[str] = []

        def record(conn, cursor, statement, params, context, executemany):
            statements.append(statement)

        event.listen(app.state.engine.sync_engine, "before_cursor_execute", record)
        try:
            r = await client.get("/api/v1/roadmap", headers=auth["headers"])
            assert r.status_code == 200
        finally:
            event.remove(app.state.engine.sync_engine, "before_cursor_execute", record)
        tts_queries = [s for s in statements if "tts_cache" in s]
        assert len(tts_queries) == 1, tts_queries


class TestScenarios:
    async def test_a1_scenarios_listed_with_opening_lines(self, client):
        auth = await register_and_login(client)
        r = await client.get("/api/v1/scenarios", headers=auth["headers"])
        assert r.status_code == 200
        scenarios = r.json()
        titles = [s["title"] for s in scenarios]
        # A fresh user is A1: both A1 scenarios show, the A2 family visit doesn't.
        assert titles == ["Kimironko market run", "Urugendo rwa moto"]

        kimironko = scenarios[0]
        assert kimironko["persona"]["name"] == "Mukamana"
        assert kimironko["persona"]["role"] == "vegetable vendor"
        assert kimironko["min_cefr"] == "A1"
        assert kimironko["umuco_tip"]
        assert len(kimironko["goals"]) == 4
        assert kimironko["voice_id"]

        # Contract: every persona carries an opening_line {ky, en} — the
        # persona's first message, served without an LLM call.
        for s in scenarios:
            line = s["persona"]["opening_line"]
            assert line["ky"] and line["en"]

        moto = scenarios[1]
        assert moto["persona"]["name"] == "Eric"
        assert moto["persona"]["opening_line"]["ky"] == "Muraho! Urashaka kujya he?"
        assert "greet the driver" in moto["goals"]

    async def test_a2_user_sees_family_visit(self, client, pg_url):
        import psycopg

        auth = await register_and_login(client)
        with psycopg.connect(pg_url) as conn:
            conn.execute(
                "UPDATE sauti.profiles SET placed_level = 'A2' WHERE user_id = %s",
                (auth["user"]["id"],),
            )
            conn.commit()
        r = await client.get("/api/v1/scenarios", headers=auth["headers"])
        titles = [s["title"] for s in r.json()]
        assert titles == ["Kimironko market run", "Urugendo rwa moto", "Gusura umuryango"]
        family = r.json()[2]
        assert family["persona"]["name"] == "Mama Chantal"
        assert family["min_cefr"] == "A2"
        assert family["persona"]["opening_line"]["ky"].startswith("Mwiriwe neza!")


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
