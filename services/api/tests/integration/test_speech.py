"""Speech endpoints — stub determinism + the real backend behind a fake ASR seam."""
from __future__ import annotations

import httpx

from tests.conftest import register_and_login


async def first_item(client, headers) -> dict:
    r = await client.get("/api/v1/roadmap", headers=headers)
    return r.json()["levels"][0]["units"][0]["lessons"][0]["items"][0]


class TestUploadFlow:
    async def test_upload_url_then_put_then_score(self, client):
        auth = await register_and_login(client)
        r = await client.post(
            "/api/v1/speech/upload-url",
            json={"content_type": "audio/webm"},
            headers=auth["headers"],
        )
        assert r.status_code == 200
        body = r.json()
        assert body["audio_ref"].startswith("user-")
        assert body["audio_ref"].endswith(".webm")
        assert body["upload_url"].endswith(f"/api/v1/speech/upload/{body['audio_ref']}")

        # PUT like a signed URL — no Authorization header (browser fetch).
        r = await client.put(
            f"/api/v1/speech/upload/{body['audio_ref']}", content=b"fake-opus-bytes"
        )
        assert r.status_code == 204

        item = await first_item(client, auth["headers"])
        r = await client.post(
            "/api/v1/speech/score",
            json={"item_id": item["id"], "audio_ref": body["audio_ref"]},
            headers=auth["headers"],
        )
        assert r.status_code == 200
        report = r.json()
        assert 60 <= report["overall"] <= 95
        assert len(report["phonemes"]) == len(item["phoneme_ref"]["syllables"])
        for p in report["phonemes"]:
            assert 0 <= p["score"] <= 100
        assert isinstance(report["tone_flags"], list)

    async def test_traversal_ref_rejected(self, client):
        r = await client.put("/api/v1/speech/upload/..%2F..%2Fetc", content=b"x")
        assert r.status_code == 404


class TestScoreDeterminism:
    async def test_same_inputs_same_report(self, client):
        auth = await register_and_login(client)
        item = await first_item(client, auth["headers"])
        payload = {"item_id": item["id"], "audio_ref": "user-fixed.webm"}
        r1 = await client.post("/api/v1/speech/score", json=payload, headers=auth["headers"])
        r2 = await client.post("/api/v1/speech/score", json=payload, headers=auth["headers"])
        assert r1.json() == r2.json()

    async def test_different_takes_differ(self, client):
        auth = await register_and_login(client)
        item = await first_item(client, auth["headers"])
        r1 = await client.post(
            "/api/v1/speech/score",
            json={"item_id": item["id"], "audio_ref": "user-take1.webm"},
            headers=auth["headers"],
        )
        r2 = await client.post(
            "/api/v1/speech/score",
            json={"item_id": item["id"], "audio_ref": "user-take2.webm"},
            headers=auth["headers"],
        )
        assert r1.json() != r2.json()


def swap_in_real_backend(app, handler) -> None:
    """Replace the stub gateway with a RealSpeechBackend whose ASR client is an
    httpx.MockTransport — real scoring code, no real NeMo service ever needed."""
    from sauti.speech.cache import CloudinaryAudioCache
    from sauti.speech.real import RealSpeechBackend

    settings = app.state.settings
    cache = CloudinaryAudioCache(
        cloud_name="", api_key="", api_secret="",
        sessionmaker=None, local_dir=settings.tts_dir,
    )
    app.state.speech_gateway = RealSpeechBackend(
        settings.audio_dir,
        settings.tts_dir,
        voice_service_url="http://voice.invalid",
        cache=cache,
        asr_transport=httpx.MockTransport(handler),
    )


async def upload_take(client, headers) -> str:
    r = await client.post(
        "/api/v1/speech/upload-url", json={"content_type": "audio/webm"}, headers=headers
    )
    ref = r.json()["audio_ref"]
    r = await client.put(f"/api/v1/speech/upload/{ref}", content=b"fake-opus-bytes")
    assert r.status_code == 204
    return ref


class TestRealScoring:
    async def test_matching_transcript_scores_high_with_transcript(self, app, client):
        auth = await register_and_login(client)
        item = await first_item(client, auth["headers"])
        swap_in_real_backend(
            app, lambda req: httpx.Response(200, json={"text": item["sentence"]})
        )
        ref = await upload_take(client, auth["headers"])
        r = await client.post(
            "/api/v1/speech/score",
            json={"item_id": item["id"], "audio_ref": ref},
            headers=auth["headers"],
        )
        assert r.status_code == 200
        report = r.json()
        assert report["overall"] >= 95
        assert report["transcript"] == item["sentence"]
        assert len(report["phonemes"]) == len(item["phoneme_ref"]["syllables"])

    async def test_wrong_transcript_scores_low(self, app, client):
        auth = await register_and_login(client)
        item = await first_item(client, auth["headers"])
        swap_in_real_backend(
            app, lambda req: httpx.Response(200, json={"text": "ibirayi bishyushye cyane"})
        )
        ref = await upload_take(client, auth["headers"])
        r = await client.post(
            "/api/v1/speech/score",
            json={"item_id": item["id"], "audio_ref": ref},
            headers=auth["headers"],
        )
        assert r.status_code == 200
        assert r.json()["overall"] <= 40

    async def test_asr_down_maps_to_503(self, app, client):
        auth = await register_and_login(client)
        item = await first_item(client, auth["headers"])

        def down(req):
            raise httpx.ConnectError("ASR down")

        swap_in_real_backend(app, down)
        ref = await upload_take(client, auth["headers"])
        r = await client.post(
            "/api/v1/speech/score",
            json={"item_id": item["id"], "audio_ref": ref},
            headers=auth["headers"],
        )
        assert r.status_code == 503
        assert r.json()["code"] == "STT_UNAVAILABLE"

    async def test_unknown_audio_ref_404(self, app, client):
        auth = await register_and_login(client)
        item = await first_item(client, auth["headers"])
        swap_in_real_backend(app, lambda req: httpx.Response(200, json={"text": "x"}))
        r = await client.post(
            "/api/v1/speech/score",
            json={"item_id": item["id"], "audio_ref": "user-never-uploaded.webm"},
            headers=auth["headers"],
        )
        assert r.status_code == 404


class TestTts:
    async def test_tts_redirects_to_playable_wav_without_auth(self, client):
        auth = await register_and_login(client)
        item = await first_item(client, auth["headers"])
        # No Authorization header — <audio src> can't send one.
        r = await client.get(f"/api/v1/tts/{item['id']}")
        assert r.status_code == 302
        location = r.headers["location"]
        assert "/api/v1/speech/audio/" in location
        r = await client.get(location)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("audio/wav")
        assert r.content[:4] == b"RIFF"

    async def test_tts_cached_stable_target(self, client):
        auth = await register_and_login(client)
        item = await first_item(client, auth["headers"])
        loc1 = (await client.get(f"/api/v1/tts/{item['id']}")).headers["location"]
        loc2 = (await client.get(f"/api/v1/tts/{item['id']}")).headers["location"]
        assert loc1 == loc2

    async def test_unknown_item_404(self, client):
        r = await client.get("/api/v1/tts/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404
