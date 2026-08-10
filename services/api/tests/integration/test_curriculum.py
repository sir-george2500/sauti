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


class TestLessonQuiz:
    """Every KIN lesson carries a real quiz that tests every aspect of the
    lesson — grammar application, vocabulary, usage in situation, culture."""

    ALLOWED_KINDS = {"grammar", "vocab", "usage", "culture"}

    async def _kin_lessons(self, client):
        auth = await register_and_login(client)
        r = await client.get("/api/v1/roadmap", headers=auth["headers"])
        assert r.status_code == 200
        return [
            lesson
            for lvl in r.json()["levels"]
            for u in lvl["units"]
            for lesson in u["lessons"]
        ]

    async def test_every_kin_lesson_has_a_full_quiz(self, client):
        lessons = await self._kin_lessons(client)
        assert len(lessons) == 24
        for lesson in lessons:
            quiz = lesson["quiz"]
            assert 4 <= len(quiz) <= 6, lesson["title"]
            assert [question["ord"] for question in quiz] == list(range(1, len(quiz) + 1))
            kinds = {question["kind"] for question in quiz}
            assert kinds <= self.ALLOWED_KINDS, lesson["title"]
            assert len(kinds) >= 2, lesson["title"]
            item_ids = {i["id"] for i in lesson["items"]}
            for question in quiz:
                assert question["question"], lesson["title"]
                assert question["explanation"], lesson["title"]
                assert len(question["options"]) == 4
                assert sum(1 for o in question["options"] if o["correct"]) == 1
                if question["item_id"] is not None:
                    # Attempts posted against this id must feed a lesson item.
                    assert question["item_id"] in item_ids, lesson["title"]

    async def test_quiz_covers_culture_where_lesson_has_a_note(self, client):
        lessons = await self._kin_lessons(client)
        for lesson in lessons:
            if lesson["culture_note"]:
                kinds = {question["kind"] for question in lesson["quiz"]}
                assert "culture" in kinds, lesson["title"]

    async def test_quick_check_mirrors_first_quiz_question(self, client):
        lessons = await self._kin_lessons(client)
        for lesson in lessons:
            quiz = lesson["quiz"]
            qc = lesson["quick_check"]
            assert qc["question"] == quiz[0]["question"], lesson["title"]
            assert qc["options"] == quiz[0]["options"], lesson["title"]

    async def test_skeleton_courses_keep_derived_quick_check(self, client):
        auth = await register_and_login(client, email="fra@example.com", course_code="FRA")
        r = await client.get("/api/v1/roadmap", headers=auth["headers"])
        assert r.status_code == 200
        lesson = r.json()["levels"][0]["units"][0]["lessons"][0]
        assert lesson["quiz"] == []  # no authored quiz for skeletons
        assert lesson["quick_check"]["question"]  # legacy fallback still works


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


class TestItemPronunciation:
    """Item payloads carry an English respelling of the sentence, because
    Kinyarwanda spelling is not Kinyarwanda pronunciation (`Ikinyarwanda` is
    said ee-chee-nyah-RWAHN-dah). It is derived from data already on the item,
    so it must cost nothing."""

    @staticmethod
    def _roadmap_items(body: dict) -> dict:
        return {
            i["sentence"]: i
            for lvl in body["levels"]
            for u in lvl["units"]
            for les in u["lessons"]
            for i in les["items"]
        }

    async def test_roadmap_items_carry_pronunciation(self, client):
        auth = await register_and_login(client)
        r = await client.get("/api/v1/roadmap", headers=auth["headers"])
        assert r.status_code == 200
        items = self._roadmap_items(r.json())
        assert items["Mwaramutse!"]["pronunciation"] == "mwah-rah-MOOT-seh!"
        assert items["Muraho!"]["pronunciation"] == "moo-rah-HOH!"
        assert items["Urakoze cyane."]["pronunciation"] == "oo-rah-KOH-zeh KYAH-neh."
        assert (
            items["Umwarimu yigisha Ikinyarwanda."]["pronunciation"]
            == "oo-mwah-REE-moo yee-GYEE-shah ee-kyee-nyah-RWAHN-dah."
        )
        # Every seeded item gets one — a blank line in the UI would be a bug.
        assert all(i["pronunciation"] for i in items.values())

    async def test_vocab_deck_items_carry_pronunciation(self, client):
        auth = await register_and_login(client)
        r = await client.get("/api/v1/vocab/decks/greetings", headers=auth["headers"])
        assert r.status_code == 200
        items = {i["sentence"]: i for i in r.json()["items"]}
        assert items["Mwiriwe neza."]["pronunciation"] == "mwee-REE-weh NEH-zah."
        assert items["Ijoro ryiza."]["pronunciation"] == "ee-JOH-roh RYEE-zah."
        assert all(i["pronunciation"] for i in r.json()["items"])

    async def test_the_same_word_reads_the_same_way_across_endpoints(self, client):
        auth = await register_and_login(client)
        roadmap = await client.get("/api/v1/roadmap", headers=auth["headers"])
        deck = await client.get("/api/v1/vocab/decks/market", headers=auth["headers"])
        items = self._roadmap_items(roadmap.json())
        for i in deck.json()["items"]:
            assert i["pronunciation"] == items[i["sentence"]]["pronunciation"]

    async def test_skeleton_courses_get_no_pronunciation(self, client):
        """French and Swahili items must NOT be respelled — "Bonjour !" through
        Kinyarwanda rules comes out "BOHN-johoo", and Swahili `ki` is a plain
        "kee" (kitabu), not the Kinyarwanda "chi"."""
        for email, code in (("fra@example.com", "FRA"), ("swa@example.com", "SWA")):
            auth = await register_and_login(client, email=email, course_code=code)
            r = await client.get("/api/v1/roadmap", headers=auth["headers"])
            assert r.status_code == 200
            items = self._roadmap_items(r.json())
            assert items, code
            assert all(i["pronunciation"] is None for i in items.values()), code

            decks = await client.get("/api/v1/vocab/decks", headers=auth["headers"])
            tag = decks.json()["decks"][0]["tag"]
            d = await client.get(f"/api/v1/vocab/decks/{tag}", headers=auth["headers"])
            assert all(i["pronunciation"] is None for i in d.json()["items"]), code

    async def test_pronunciation_costs_no_extra_query(self, app, client, monkeypatch):
        """Derived at serialization time from `sentence` + `phoneme_ref`, both
        already loaded. Turning the respelling off must not change the SQL."""
        from sqlalchemy import event

        auth = await register_and_login(client)

        async def sql_for(path: str) -> tuple[list[str], dict]:
            statements: list[str] = []

            def record(conn, cursor, statement, params, context, executemany):
                statements.append(statement)

            event.listen(app.state.engine.sync_engine, "before_cursor_execute", record)
            try:
                r = await client.get(path, headers=auth["headers"])
                assert r.status_code == 200
                return statements, r.json()
            finally:
                event.remove(app.state.engine.sync_engine, "before_cursor_execute", record)

        for path, has_pron in (
            ("/api/v1/roadmap", lambda b: all(
                i["pronunciation"] for i in TestItemPronunciation._roadmap_items(b).values()
            )),
            ("/api/v1/vocab/decks/food", lambda b: all(i["pronunciation"] for i in b["items"])),
        ):
            await client.get(path, headers=auth["headers"])  # warm any first-call SQL
            with_pron, body = await sql_for(path)
            assert has_pron(body), path  # the field really is being computed

            monkeypatch.setattr("sauti.schemas.curriculum.respell", lambda *a, **k: None)
            without_pron, body = await sql_for(path)
            monkeypatch.undo()
            assert not has_pron(body), path  # ...and the patch really disabled it

            assert with_pron == without_pron, path


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
