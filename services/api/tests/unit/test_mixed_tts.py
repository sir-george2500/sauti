"""RealSpeechBackend.tts_mixed — the synthesize-once path for a mixed reply.

The voice service and Cloudinary are both faked; what is under test is what we
send, what we cache it under, and that a repeated reply costs nothing.
"""
from __future__ import annotations

import json

import httpx
import pytest

from sauti.speech.cache import CloudinaryAudioCache, cache_key
from sauti.speech.gateway import MIXED_VOICE, StubSpeechBackend
from sauti.speech.real import RealSpeechBackend
from sauti.speech.segmentation import mixed_key_text, segment_reply, segments_payload

WAV = b"RIFF....WAVEmixed"

REPLY = (
    "Today you learned greetings! For example, 'Mwaramutse' means "
    "'Good morning!' and 'Mwiriwe' means 'Good afternoon.'"
)


class FakeVoiceService:
    def __init__(self) -> None:
        self.mixed_bodies: list[dict] = []
        self.status = 200

    def handler(self, request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/tts/mixed"
        self.mixed_bodies.append(json.loads(request.read()))
        if self.status != 200:
            return httpx.Response(self.status, content=b"boom")
        return httpx.Response(200, content=WAV, headers={"content-type": "audio/wav"})


class FakeCloudinary:
    """Accepts every upload and serves it back at the deterministic URL."""

    def __init__(self) -> None:
        self.assets: set[str] = set()
        self.uploads = 0

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.method == "HEAD":
            return httpx.Response(200 if request.url.path in self.assets else 404)
        self.uploads += 1
        key = request.read().split(b"sauti/tts/")[1].split(b"\r\n")[0].decode()
        self.assets.add(f"/testcloud/video/upload/sauti/tts/{key}.wav")
        return httpx.Response(
            200,
            content=json.dumps(
                {
                    "secure_url": "https://res.cloudinary.com/testcloud/video/"
                    f"upload/v1/sauti/tts/{key}.wav"
                }
            ),
        )


@pytest.fixture()
def voice() -> FakeVoiceService:
    return FakeVoiceService()


@pytest.fixture()
def backend(tmp_path, voice) -> RealSpeechBackend:
    cloud = FakeCloudinary()
    cache = CloudinaryAudioCache(
        cloud_name="testcloud",
        api_key="key",
        api_secret="secret",
        sessionmaker=None,
        local_dir=str(tmp_path / "tts"),
        local_base_url="http://testserver",
        transport=httpx.MockTransport(cloud.handler),
    )
    b = RealSpeechBackend(
        str(tmp_path / "audio"),
        str(tmp_path / "tts"),
        voice_service_url="http://voice:8093",
        cache=cache,
        voice_transport=httpx.MockTransport(voice.handler),
    )
    b.cloud = cloud  # for assertions
    return b


class TestTtsMixed:
    async def test_posts_every_span_with_its_voice(self, backend, voice):
        segments = segments_payload(segment_reply(REPLY, ["Mwaramutse!", "Mwiriwe."]))
        url = await backend.tts_mixed(segments)

        assert url.startswith("https://res.cloudinary.com/")
        assert len(voice.mixed_bodies) == 1
        sent = voice.mixed_bodies[0]["segments"]
        assert [s["lang"] for s in sent] == ["en", "rw", "en", "rw", "en"]
        assert [s["text"] for s in sent] == [s["text"] for s in segments]
        # Kinyarwanda spans name a speaker; English is Kokoro's single voice.
        assert all(s["voice"] == "female" for s in sent if s["lang"] == "rw")
        assert all("voice" not in s for s in sent if s["lang"] == "en")

    async def test_repeated_reply_is_free(self, backend, voice):
        segments = segments_payload(segment_reply(REPLY, ["Mwaramutse!"]))
        first = await backend.tts_mixed(segments)
        second = await backend.tts_mixed(list(segments))  # a fresh, equal list

        assert second == first
        assert len(voice.mixed_bodies) == 1  # synthesized exactly once
        assert backend.cloud.uploads == 1

    async def test_key_is_the_whole_span_list_not_just_the_words(self, backend, voice):
        """Same words, different languages = a different clip, so a different key."""
        a = [{"text": "Mwiriwe", "lang": "rw"}]
        b = [{"text": "Mwiriwe", "lang": "en"}]
        assert await backend.tts_mixed(a) != await backend.tts_mixed(b)
        assert len(voice.mixed_bodies) == 2

    async def test_cache_key_matches_the_documented_scheme(self, backend):
        segments = [{"text": "Muraho", "lang": "rw"}]
        url = await backend.tts_mixed(segments)
        assert cache_key(MIXED_VOICE, mixed_key_text(segments)) in url

    async def test_voice_service_error_propagates_for_the_caller_to_swallow(
        self, backend, voice
    ):
        voice.status = 503
        with pytest.raises(httpx.HTTPStatusError):
            await backend.tts_mixed([{"text": "Muraho", "lang": "rw"}])


class TestStubTtsMixed:
    async def test_stub_returns_a_playable_ref_keyed_on_the_spans(self, tmp_path):
        stub = StubSpeechBackend(str(tmp_path / "audio"), str(tmp_path / "tts"))
        segments = segments_payload(segment_reply(REPLY, ["Mwaramutse!"]))

        ref = await stub.tts_mixed(segments)
        assert await stub.tts_mixed(list(segments)) == ref  # deterministic
        assert await stub.tts_mixed([{"text": "other", "lang": "en"}]) != ref

        path = stub.audio_path(ref)
        assert path is not None and path.read_bytes()[:4] == b"RIFF"
