"""RealSpeechBackend — YourTTS Kinyarwanda (rent-rwanda voice service) behind
the CloudinaryAudioCache, so every phrase is synthesized exactly once.

STT and pronunciation scoring stay on the deterministic stub (no real
FastConformer/scorer in this slice) — inherited from StubSpeechBackend, which
also keeps the upload-ref plumbing and local audio serving (the cache's
degradation path serves WAVs from the same tts_dir).
"""
from __future__ import annotations

import httpx

from sauti.speech.cache import CloudinaryAudioCache
from sauti.speech.gateway import StubSpeechBackend

SYNTH_TIMEOUT_S = 120.0  # cold model load can take a while; warm rw is ~1.4 s


class RealSpeechBackend(StubSpeechBackend):
    tts_inline = False  # synthesis takes seconds — send text first, audio follows

    def __init__(
        self,
        audio_dir: str,
        tts_dir: str,
        voice_service_url: str,
        cache: CloudinaryAudioCache,
        default_lang: str = "rw",
    ):
        super().__init__(audio_dir, tts_dir)
        self._voice_url = voice_service_url.rstrip("/")
        self.cache = cache
        self._default_lang = default_lang

    def _lang(self, voice: str | None) -> str:
        # All seeded voices are Kinyarwanda (Diane · Kigali). When English-gloss
        # or French voices land, map voice ids -> lang here — this class stays
        # the only place that knows backend/model names (SPEC §4).
        return self._default_lang

    async def _synthesize(self, text: str, lang: str) -> bytes:
        async with httpx.AsyncClient(timeout=SYNTH_TIMEOUT_S) as client:
            resp = await client.post(
                f"{self._voice_url}/tts", json={"text": text, "lang": lang}
            )
            resp.raise_for_status()
            return resp.content

    async def tts(self, text: str, voice: str | None = None, cache_key: str | None = None) -> str:
        """Returns a full URL (Cloudinary secure_url, or a local /speech/audio/
        URL when Cloudinary is unreachable). Raises if synthesis itself fails —
        callers degrade gracefully (frame without audio / 503)."""
        lang = self._lang(voice)

        async def synth() -> bytes:
            return await self._synthesize(text, lang)

        return await self.cache.get_or_create(text, voice or "", synth)
