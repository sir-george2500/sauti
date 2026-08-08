"""Sauti voice service — Kinyarwanda YourTTS (female Diane / male Emmanuel)
plus English Kokoro (af_heart), and a mixed-language endpoint that stitches
both into ONE clip.

Why mixed: Mwarimu (the study buddy) writes English with Kinyarwanda quoted
inside — "…'Mwaramutse' means 'Good morning'". Speaking that with an English
voice mangles the Kinyarwanda, which is unacceptable in a pronunciation-teaching
product. POST /tts/mixed takes the already-segmented reply and returns a single
WAV whose voice switches per span.

Concatenation happens HERE (numpy/soundfile live in this venv, not in the API):
every engine's output is resampled to OUT_RATE, peak-normalized so the two
models sit at a comparable level, and joined with a short pause.

rent-rwanda's assistant_app only exposes the female Kinyarwanda voice; its
engine layer (engine_yourtts.YourTtsEngine, engine_kokoro.KokoroEngine) is
imported unmodified from VOICE_ENGINE_DIR.

Run with rent-rwanda's coqui venv (see README.md):
    cd services/voice && \
    /home/delta-x/rent-rwanda/services/voice/.venv-yourtts/bin/uvicorn tts_app:app --port 8093

    POST /tts       {text, lang: "rw"|"en", voice: "female"|"male"} -> audio/wav
    POST /tts/mixed {segments: [{text, lang, voice?}]}              -> audio/wav
    GET  /health -> {ok, voices: {female: bool, male: bool, en: bool}}

Every voice is lazily loaded, warmed in a startup daemon thread, and repeat
requests are served from a small bounded FIFO cache.
"""
from __future__ import annotations

import io
import json
import os
import sys
import threading

from fastapi import Body, FastAPI
from fastapi.responses import JSONResponse, Response

# Engine modules (engine_yourtts, engine_kokoro + their deps) live in the
# rent-rwanda voice service — imported, never modified. Override for other
# checkouts.
VOICE_ENGINE_DIR = os.environ.get(
    "VOICE_ENGINE_DIR", "/home/delta-x/rent-rwanda/services/voice"
)
sys.path.insert(0, VOICE_ENGINE_DIR)

app = FastAPI(title="Sauti voice service (Kinyarwanda YourTTS + English Kokoro)")

# Engine keys. Kinyarwanda has two speakers; English has one (Kokoro af_heart,
# Apache-2.0 — commercially safe, unlike YourTTS's English checkpoints).
RW_VOICES = ("female", "male")
EN_VOICE = "en"
VOICES = (*RW_VOICES, EN_VOICE)

# Uniform output sample rate for /tts/mixed. 24 kHz is Kokoro's native rate and
# above YourTTS's, so the English half is never resampled and the Kinyarwanda
# half is only ever upsampled (no lost band).
OUT_RATE = 24_000
# Pause inserted between spans — long enough to read as a natural clause break,
# short enough that a three-span reply doesn't drag.
GAP_S = 0.15
# Each span is peak-normalized to this before joining: the two models are
# trained separately and land at noticeably different loudness.
PEAK = 0.85

_engines: dict[str, object] = {}
_ready: dict[str, bool] = {v: False for v in VOICES}
_lock = threading.Lock()

# Bounded FIFO response cache: identical request -> WAV bytes.
_cache: dict[tuple[str, str], bytes] = {}
_CACHE_MAX = 256


def _cache_get(key: tuple[str, str]) -> bytes | None:
    return _cache.get(key)


def _cache_put(key: tuple[str, str], wav: bytes) -> None:
    if len(_cache) >= _CACHE_MAX:
        _cache.pop(next(iter(_cache)))
    _cache[key] = wav


def _engine(voice: str):
    with _lock:
        if voice not in _engines:
            if voice == EN_VOICE:
                from engine_kokoro import KokoroEngine

                _engines[voice] = KokoroEngine()
            else:
                from engine_yourtts import YourTtsEngine

                _engines[voice] = YourTtsEngine(voice=voice)
        return _engines[voice]


def _synth_pcm(voice: str, text: str):
    """(sample_rate, float32 mono) straight from the engine."""
    rate, audio = _engine(voice).synth(text)
    _ready[voice] = True
    return int(rate), audio


def _wav_bytes(audio, rate: int, subtype: str | None = None) -> bytes:
    import soundfile as sf

    buf = io.BytesIO()
    sf.write(buf, audio, rate, format="WAV", subtype=subtype)
    return buf.getvalue()


def _synth_wav(voice: str, text: str) -> bytes:
    rate, audio = _synth_pcm(voice, text)
    return _wav_bytes(audio, rate)


# -- mixed-language concatenation -------------------------------------------


def _resample(audio, rate: int, target: int):
    import numpy as np

    if rate == target:
        return np.asarray(audio, dtype=np.float32)
    from fractions import Fraction

    from scipy.signal import resample_poly

    ratio = Fraction(target, rate).limit_denominator(1000)
    out = resample_poly(np.asarray(audio, dtype=np.float32), ratio.numerator, ratio.denominator)
    return np.asarray(out, dtype=np.float32)


def _trim(audio):
    """Drop each engine's leading/trailing silence.

    YourTTS pads ~0.6 s of near-silence onto every clip; left in, a five-span
    reply gains three seconds of dead air and the voice switch stops reading as
    one sentence. A small margin is kept so plosives are not clipped.
    """
    import numpy as np

    if audio.size == 0:
        return audio
    peak = float(np.max(np.abs(audio)))
    if peak <= 1e-6:
        return audio[:0]
    loud = np.flatnonzero(np.abs(audio) > peak * 0.01)
    if loud.size == 0:
        return audio[:0]
    margin = int(0.02 * OUT_RATE)
    return audio[max(0, int(loud[0]) - margin) : int(loud[-1]) + margin]


def _normalize(audio):
    import numpy as np

    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak <= 1e-6:
        return audio
    return np.asarray(audio * (PEAK / peak), dtype=np.float32)


def _voice_for(lang: str, voice: str | None) -> str | None:
    """Engine key for a segment, or None when the segment is unroutable."""
    if lang == "en":
        return EN_VOICE
    if lang == "rw":
        return voice if voice in RW_VOICES else "female"
    return None


def _synth_mixed(segments: list[dict]) -> bytes:
    """One WAV at OUT_RATE: each span in its own voice, joined by a short pause."""
    import numpy as np

    gap = np.zeros(int(GAP_S * OUT_RATE), dtype=np.float32)
    pieces: list = []
    for seg in segments:
        rate, audio = _synth_pcm(seg["voice"], seg["text"])
        piece = _normalize(_trim(_resample(audio, rate, OUT_RATE)))
        if piece.size == 0:
            continue
        if pieces:
            pieces.append(gap)
        pieces.append(piece)
    if not pieces:
        return _wav_bytes(np.zeros(1, dtype=np.float32), OUT_RATE, subtype="PCM_16")
    joined = np.concatenate(pieces)
    # PCM_16 rather than the float WAV /tts emits: a mixed clip is played by
    # every browser we support and is half the bytes over the wire.
    return _wav_bytes(joined, OUT_RATE, subtype="PCM_16")


# -- app ---------------------------------------------------------------------


@app.on_event("startup")
def _warm() -> None:
    """Load + warm every voice off the request path (model download on first run)."""

    def warm() -> None:
        for voice in VOICES:
            try:
                _synth_wav(voice, "Muraho." if voice in RW_VOICES else "Hello.")
                print(f"[warm] {voice} voice ready", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"[warm] {voice} failed: {exc}", flush=True)

    threading.Thread(target=warm, daemon=True).start()


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({"ok": True, "voices": dict(_ready)})


@app.post("/tts")
def tts(payload: dict = Body(...)) -> Response:
    text = (payload.get("text") or "").strip()
    if not text:
        return Response(status_code=400, content="empty text")
    lang = payload.get("lang") or "rw"
    if lang not in ("rw", "en"):
        return Response(status_code=400, content=f"unsupported lang '{lang}' (rw|en)")
    voice = payload.get("voice") or ("female" if lang == "rw" else EN_VOICE)
    if lang == "rw" and voice not in RW_VOICES:
        return Response(status_code=400, content=f"unknown voice '{voice}'")
    if lang == "en":
        voice = EN_VOICE

    key = (voice, text)
    wav = _cache_get(key)
    if wav is None:
        wav = _synth_wav(voice, text)
        _cache_put(key, wav)
    return Response(content=wav, media_type="audio/wav")


@app.post("/tts/mixed")
def tts_mixed(payload: dict = Body(...)) -> Response:
    """{segments: [{text, lang: "rw"|"en", voice?: "female"|"male"}]} -> ONE WAV.

    Empty/whitespace-only segments are skipped; a request with nothing left to
    say is a 400, exactly like POST /tts with empty text.
    """
    raw = payload.get("segments")
    if not isinstance(raw, list):
        return Response(status_code=400, content="segments must be a list")

    segments: list[dict] = []
    for seg in raw:
        if not isinstance(seg, dict):
            return Response(status_code=400, content="each segment must be an object")
        text = (seg.get("text") or "").strip()
        if not text:
            continue  # nothing to speak — silently skipped, not an error
        lang = seg.get("lang") or "rw"
        voice = _voice_for(lang, seg.get("voice"))
        if voice is None:
            return Response(status_code=400, content=f"unsupported lang '{lang}' (rw|en)")
        segments.append({"text": text, "lang": lang, "voice": voice})

    if not segments:
        return Response(status_code=400, content="no speakable segments")

    key = ("mixed", json.dumps(segments, ensure_ascii=False, sort_keys=True))
    wav = _cache_get(key)
    if wav is None:
        wav = _synth_mixed(segments)
        _cache_put(key, wav)
    return Response(content=wav, media_type="audio/wav")
