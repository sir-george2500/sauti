"""SpeechGateway — the only class that knows backend/model names.

MVP backend is a deterministic stub (hash-seeded scores so e2e is stable).
Real YourTTS / FastConformer servers slot in behind the same interface later.
"""
from __future__ import annotations

import hashlib
import math
import struct
import time
import uuid
import wave
from pathlib import Path
from typing import Protocol, runtime_checkable

from sauti.schemas.common import PhonemeScore, PronReport


@runtime_checkable
class SpeechGateway(Protocol):
    def tts(self, text: str, voice: str | None = None, cache_key: str | None = None) -> str:
        """Synthesize `text`, return an audio_ref servable by the audio endpoint."""
        ...

    def stt(self, audio_ref: str, lang: str) -> str: ...

    def score(self, audio_ref: str, item_id: str, phoneme_ref: dict) -> PronReport: ...


def _seed(*parts: str) -> int:
    return int.from_bytes(hashlib.sha256("|".join(parts).encode()).digest()[:8], "big")


class StubSpeechBackend:
    """Deterministic stand-in. Scores are hash-seeded from (item_id, audio_ref);
    TTS renders a short sine-tone WAV per text (cached on disk)."""

    # An upload URL is only PUT-able for this long after being issued
    # (signed-URL expiry stand-in). Retries within the window are fine.
    UPLOAD_TTL_S = 15 * 60

    def __init__(self, audio_dir: str, tts_dir: str):
        self.audio_dir = Path(audio_dir)
        self.tts_dir = Path(tts_dir)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.tts_dir.mkdir(parents=True, exist_ok=True)
        # Issued-and-not-expired upload refs. In-memory like the rate limiter:
        # swap for a shared store when running more than one node/worker.
        self._pending_uploads: dict[str, float] = {}

    # -- storage helpers used by the upload endpoints ------------------------
    def new_upload_ref(self, content_type: str) -> str:
        ext = {
            "audio/webm": "webm", "audio/ogg": "ogg", "audio/wav": "wav",
            "audio/mpeg": "mp3", "audio/mp4": "m4a",
        }.get(content_type.split(";")[0].strip(), "bin")
        ref = f"user-{uuid.uuid4().hex}.{ext}"
        self._prune_pending()
        self._pending_uploads[ref] = time.monotonic() + self.UPLOAD_TTL_S
        return ref

    def upload_ref_valid(self, ref: str) -> bool:
        """True only for refs this server issued that haven't expired — the PUT
        endpoint is public, so it must not accept attacker-minted refs."""
        self._prune_pending()
        return ref in self._pending_uploads

    def _prune_pending(self) -> None:
        now = time.monotonic()
        expired = [r for r, exp in self._pending_uploads.items() if exp <= now]
        for r in expired:
            del self._pending_uploads[r]

    def save_upload(self, audio_ref: str, data: bytes) -> None:
        safe = Path(audio_ref).name  # no traversal
        (self.audio_dir / safe).write_bytes(data)

    def audio_path(self, audio_ref: str) -> Path | None:
        safe = Path(audio_ref).name
        for base in (self.tts_dir, self.audio_dir):
            p = base / safe
            if p.exists():
                return p
        return None

    # -- gateway interface ---------------------------------------------------
    def tts(self, text: str, voice: str | None = None, cache_key: str | None = None) -> str:
        key = cache_key or hashlib.sha256(f"{voice}|{text}".encode()).hexdigest()[:16]
        ref = f"tts-{key}.wav"
        path = self.tts_dir / ref
        if not path.exists():
            self._write_sine_wav(path, seed=_seed("tts", text, voice or ""))
        return ref

    def stt(self, audio_ref: str, lang: str) -> str:
        # Deterministic stand-in transcript; the real FastConformer replaces this.
        canned = {
            "rw": "Muraho, mwiriwe neza.",
            "sw": "Hujambo, habari yako?",
            "fr": "Bonjour, comment allez-vous ?",
        }
        return canned.get(lang, canned["rw"])

    def score(self, audio_ref: str, item_id: str, phoneme_ref: dict) -> PronReport:
        seed = _seed("score", item_id, audio_ref)
        overall = 60 + seed % 36  # 60..95
        syllables = phoneme_ref.get("syllables") or [{"syl": "??", "tone": "L"}]
        phonemes: list[PhonemeScore] = []
        tone_flags: list[str] = []
        for i, syl in enumerate(syllables):
            name = syl.get("syl", "??") if isinstance(syl, dict) else str(syl)
            tone = syl.get("tone") if isinstance(syl, dict) else None
            s = 55 + _seed("syl", item_id, audio_ref, str(i)) % 45  # 55..99
            note = None
            if s < 70:
                note = "articulate this syllable more clearly"
            if tone in ("H", "R", "F") and _seed("tone", item_id, audio_ref, str(i)) % 3 == 0:
                tone_flags.append(f"tone on '{name}' sounded flat — aim for a {'rise' if tone in ('H', 'R') else 'fall'}")
                note = note or "tone contour missed"
            phonemes.append(PhonemeScore(phoneme=name, score=s, note=note))
        return PronReport(overall=overall, phonemes=phonemes, tone_flags=tone_flags)

    # -- wav synthesis -------------------------------------------------------
    @staticmethod
    def _write_sine_wav(path: Path, seed: int, duration_s: float = 0.8, rate: int = 16000) -> None:
        freq = 220.0 + (seed % 440)  # 220..660 Hz, per-text placeholder tone
        n = int(duration_s * rate)
        frames = bytearray()
        for i in range(n):
            fade = min(1.0, i / 800, (n - i) / 800)
            val = int(12000 * fade * math.sin(2 * math.pi * freq * i / rate))
            frames += struct.pack("<h", val)
        tmp = path.with_suffix(".tmp")
        with wave.open(str(tmp), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(bytes(frames))
        tmp.rename(path)
