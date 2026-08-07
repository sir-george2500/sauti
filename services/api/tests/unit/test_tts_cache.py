"""CloudinaryAudioCache — key determinism, synth-once, fallback (Cloudinary faked)."""
from __future__ import annotations

import json

import httpx
import pytest

from sauti.speech.cache import CloudinaryAudioCache, cache_key

WAV = b"RIFF....WAVEfake"


class FakeCloudinary:
    """httpx MockTransport handler standing in for res./api.cloudinary.com."""

    def __init__(self):
        self.assets: dict[str, bytes] = {}
        self.upload_calls = 0
        self.head_calls = 0
        self.down = False

    def handler(self, request: httpx.Request) -> httpx.Response:
        if self.down:
            raise httpx.ConnectError("cloudinary unreachable", request=request)
        if request.method == "HEAD":
            self.head_calls += 1
            path = request.url.path  # /<cloud>/video/upload/sauti/tts/<key>.wav
            return httpx.Response(200 if path in self.assets else 404)
        if request.method == "POST" and request.url.path.endswith("/video/upload"):
            self.upload_calls += 1
            body = request.read()
            # public_id arrives in the multipart body; find the key crudely.
            key = body.split(b"sauti/tts/")[1].split(b"\r\n")[0].decode()
            self.assets[f"/testcloud/video/upload/sauti/tts/{key}.wav"] = WAV
            return httpx.Response(
                200,
                content=json.dumps(
                    {"secure_url": f"https://res.cloudinary.com/testcloud/video/upload/v1/sauti/tts/{key}.wav"}
                ),
            )
        return httpx.Response(404)


@pytest.fixture()
def fake_cloud() -> FakeCloudinary:
    return FakeCloudinary()


def make_cache(tmp_path, fake_cloud) -> CloudinaryAudioCache:
    return CloudinaryAudioCache(
        cloud_name="testcloud",
        api_key="key",
        api_secret="secret",
        sessionmaker=None,  # DB index off in unit tests; seam covered separately
        local_dir=str(tmp_path),
        local_base_url="http://testserver",
        transport=httpx.MockTransport(fake_cloud.handler),
    )


class TestCacheKey:
    def test_deterministic_and_voice_scoped(self):
        assert cache_key("v1", "Muraho") == cache_key("v1", "Muraho")
        assert cache_key("v1", "Muraho") != cache_key("v2", "Muraho")
        assert cache_key("v1", "Muraho") != cache_key("v1", "Mwaramutse")
        assert len(cache_key("v1", "Muraho")) == 32


class TestGetOrCreate:
    async def test_synth_called_once_then_cache_hits(self, tmp_path, fake_cloud):
        cache = make_cache(tmp_path, fake_cloud)
        calls = 0

        async def synth() -> bytes:
            nonlocal calls
            calls += 1
            return WAV

        url1 = await cache.get_or_create("Muraho", "diane", synth)
        assert calls == 1
        assert fake_cloud.upload_calls == 1
        assert url1.startswith("https://res.cloudinary.com/testcloud/video/upload/")
        assert cache_key("diane", "Muraho") in url1
        # Local copy kept for graceful degradation.
        assert (tmp_path / f"tts-{cache_key('diane', 'Muraho')}.wav").read_bytes() == WAV

        url2 = await cache.get_or_create("Muraho", "diane", synth)
        assert url2 == url1
        assert calls == 1  # never synthesize the same phrase twice
        assert fake_cloud.upload_calls == 1

    async def test_existing_remote_asset_found_via_head_without_synth(self, tmp_path, fake_cloud):
        key = cache_key("diane", "Mwaramutse")
        fake_cloud.assets[f"/testcloud/video/upload/sauti/tts/{key}.wav"] = WAV

        cache = make_cache(tmp_path, fake_cloud)  # fresh instance: empty memory

        async def synth() -> bytes:
            raise AssertionError("must not synthesize when the asset already exists")

        url = await cache.get_or_create("Mwaramutse", "diane", synth)
        assert fake_cloud.head_calls == 1
        assert url == f"https://res.cloudinary.com/testcloud/video/upload/sauti/tts/{key}.wav"

    async def test_cloudinary_down_falls_back_to_local_wav(self, tmp_path, fake_cloud):
        fake_cloud.down = True
        cache = make_cache(tmp_path, fake_cloud)

        async def synth() -> bytes:
            return WAV

        url = await cache.get_or_create("Amakuru?", "diane", synth)
        key = cache_key("diane", "Amakuru?")
        assert url == f"http://testserver/api/v1/speech/audio/tts-{key}.wav"
        assert (tmp_path / f"tts-{key}.wav").read_bytes() == WAV
        assert cache.stats["local_fallback"] == 1

    async def test_db_index_short_circuits_head_and_synth(self, tmp_path, fake_cloud):
        cache = make_cache(tmp_path, fake_cloud)
        stored = "https://res.cloudinary.com/testcloud/video/upload/v9/sauti/tts/abc.wav"

        async def db_get(key: str) -> str | None:
            return stored

        cache._db_get = db_get  # seam: fake the DB row lookup

        async def synth() -> bytes:
            raise AssertionError("must not synthesize on a DB hit")

        url = await cache.get_or_create("Murakoze", "diane", synth)
        assert url == stored
        assert fake_cloud.head_calls == 0
        assert fake_cloud.upload_calls == 0
        # Second call served from memory without touching the DB seam again.
        cache._db_get = None  # would explode if called
        assert await cache.get_or_create("Murakoze", "diane", synth) == stored
