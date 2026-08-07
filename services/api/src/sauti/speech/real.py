"""RealSpeechBackend — the real Kinyarwanda speech stack.

TTS: YourTTS via the sauti voice service (services/voice/tts_app.py, both
voices) behind the CloudinaryAudioCache, so every phrase is synthesized once.
STT: NeMo FastConformer Kinyarwanda ASR (rent-rwanda, port 8092).
Scoring: FastConformer transcript vs the item's sentence — deterministic
alignment scoring in sauti.speech.scoring (no LLM).

StubSpeechBackend is inherited for the upload-ref plumbing and local audio
serving (the cache's degradation path serves WAVs from the same tts_dir).
"""
from __future__ import annotations

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sauti.schemas.common import PronReport
from sauti.speech.cache import CloudinaryAudioCache
from sauti.speech.gateway import SpeechUnavailableError, StubSpeechBackend
from sauti.speech.scoring import score_pronunciation

SYNTH_TIMEOUT_S = 120.0  # cold model load can take a while; warm rw is ~1.4 s
STT_TIMEOUT_S = 60.0  # warm FastConformer is <1 s; leave headroom for cold start

# The gateway is the only place that knows model/voice names (SPEC §4):
# seeded speakers -> the voice param of services/voice/tts_app.py.
SPEAKER_VOICE_PARAMS = {"Diane": "female", "Emmanuel": "male"}
DEFAULT_VOICE_PARAM = "female"


class RealSpeechBackend(StubSpeechBackend):
    tts_inline = False  # synthesis takes seconds — send text first, audio follows

    def __init__(
        self,
        audio_dir: str,
        tts_dir: str,
        voice_service_url: str,
        cache: CloudinaryAudioCache,
        default_lang: str = "rw",
        asr_url: str = "http://127.0.0.1:8092",
        sessionmaker: async_sessionmaker[AsyncSession] | None = None,
        asr_transport: httpx.AsyncBaseTransport | None = None,
    ):
        super().__init__(audio_dir, tts_dir)
        self._voice_url = voice_service_url.rstrip("/")
        self.cache = cache
        self._default_lang = default_lang
        self._asr_url = asr_url.rstrip("/")
        self._sessionmaker = sessionmaker
        self._asr_transport = asr_transport  # test seam (httpx.MockTransport)
        self._voice_params: dict[str, str] | None = None  # voice_id -> female|male

    def _lang(self, voice: str | None) -> str:
        # All seeded voices are Kinyarwanda (Kigali). When English-gloss or
        # French voices land, map voice ids -> lang here — this class stays
        # the only place that knows backend/model names (SPEC §4).
        return self._default_lang

    async def _voice_param(self, voice: str | None) -> str:
        """Map a voice id (stringified Item.voice_id) to the tts_app voice param.

        The speaker map is loaded from the voices table once and cached; any
        failure degrades to the female voice rather than blocking synthesis.
        """
        if not voice:
            return DEFAULT_VOICE_PARAM
        if self._voice_params is None and self._sessionmaker is not None:
            try:
                from sauti.models import Voice  # local import — avoid cycle at module load

                async with self._sessionmaker() as db:
                    rows = list(await db.scalars(select(Voice)))
                self._voice_params = {
                    str(row.id): SPEAKER_VOICE_PARAMS.get(row.speaker, DEFAULT_VOICE_PARAM)
                    for row in rows
                }
            except Exception:  # noqa: BLE001 — voices index down must not break TTS
                return DEFAULT_VOICE_PARAM
        return (self._voice_params or {}).get(voice, DEFAULT_VOICE_PARAM)

    async def _synthesize(self, text: str, lang: str, voice_param: str) -> bytes:
        async with httpx.AsyncClient(timeout=SYNTH_TIMEOUT_S) as client:
            resp = await client.post(
                f"{self._voice_url}/tts",
                json={"text": text, "lang": lang, "voice": voice_param},
            )
            resp.raise_for_status()
            return resp.content

    # -- STT / scoring -------------------------------------------------------
    def _asr_client(self) -> httpx.AsyncClient:
        if self._asr_transport is not None:
            return httpx.AsyncClient(transport=self._asr_transport, timeout=STT_TIMEOUT_S)
        return httpx.AsyncClient(timeout=STT_TIMEOUT_S)

    async def stt(self, audio_ref: str, lang: str) -> str:
        path = self.audio_path(audio_ref)
        if path is None:
            raise FileNotFoundError(audio_ref)
        try:
            async with self._asr_client() as client:
                resp = await client.post(
                    f"{self._asr_url}/transcribe",
                    files={"file": (path.name, path.read_bytes(), "application/octet-stream")},
                )
        except httpx.HTTPError as exc:
            raise SpeechUnavailableError(f"ASR unreachable: {exc}") from exc
        if resp.status_code >= 500:
            raise SpeechUnavailableError(f"ASR error {resp.status_code}")
        if resp.status_code != 200:
            # 4xx = undecodable/empty audio — an empty transcript scores as silence.
            return ""
        return str(resp.json().get("text") or "").strip()

    async def score(
        self, audio_ref: str, item_id: str, sentence: str, phoneme_ref: dict
    ) -> PronReport:
        transcript = await self.stt(audio_ref, self._default_lang)
        return score_pronunciation(sentence, transcript, phoneme_ref)

    async def tts(self, text: str, voice: str | None = None, cache_key: str | None = None) -> str:
        """Returns a full URL (Cloudinary secure_url, or a local /speech/audio/
        URL when Cloudinary is unreachable). Raises if synthesis itself fails —
        callers degrade gracefully (frame without audio / 503)."""
        lang = self._lang(voice)
        voice_param = await self._voice_param(voice)

        async def synth() -> bytes:
            return await self._synthesize(text, lang, voice_param)

        return await self.cache.get_or_create(text, voice or "", synth)
