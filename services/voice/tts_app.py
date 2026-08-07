"""Sauti voice service — Kinyarwanda YourTTS, both voices (female Diane-style,
male Emmanuel-style), one endpoint.

rent-rwanda's assistant_app only exposes the female voice; its engine layer
(engine_yourtts.YourTtsEngine) already supports voice="male"
(DigitalUmuganda/Kinyarwanda_YourTTS_v1). This thin app imports those engine
modules unmodified from VOICE_ENGINE_DIR and exposes the voice parameter.

Run with rent-rwanda's coqui venv (see README.md):
    cd services/voice && \
    /home/delta-x/rent-rwanda/services/voice/.venv-yourtts/bin/uvicorn tts_app:app --port 8093

    POST /tts {text, lang: "rw", voice: "female"|"male"} -> audio/wav
    GET  /health -> {ok, voices: {female: bool, male: bool}}

Both voices are lazily loaded, warmed in a startup daemon thread, and repeat
requests are served from a small bounded FIFO cache.
"""
from __future__ import annotations

import io
import os
import sys
import threading

from fastapi import Body, FastAPI
from fastapi.responses import JSONResponse, Response

# Engine modules (engine_yourtts + its deps) live in the rent-rwanda voice
# service — imported, never modified. Override for other checkouts.
VOICE_ENGINE_DIR = os.environ.get(
    "VOICE_ENGINE_DIR", "/home/delta-x/rent-rwanda/services/voice"
)
sys.path.insert(0, VOICE_ENGINE_DIR)

app = FastAPI(title="Sauti voice service (Kinyarwanda YourTTS, two voices)")

VOICES = ("female", "male")

_engines: dict[str, object] = {}
_ready: dict[str, bool] = {v: False for v in VOICES}
_lock = threading.Lock()

# Bounded FIFO response cache: identical (voice, text) -> WAV bytes.
_cache: dict[tuple[str, str], bytes] = {}
_CACHE_MAX = 256


def _engine(voice: str):
    with _lock:
        if voice not in _engines:
            from engine_yourtts import YourTtsEngine

            _engines[voice] = YourTtsEngine(voice=voice)
        return _engines[voice]


def _synth_wav(voice: str, text: str) -> bytes:
    import soundfile as sf

    rate, audio = _engine(voice).synth(text)
    buf = io.BytesIO()
    sf.write(buf, audio, rate, format="WAV")
    _ready[voice] = True
    return buf.getvalue()


@app.on_event("startup")
def _warm() -> None:
    """Load + warm both voices off the request path (model download on first run)."""

    def warm() -> None:
        for voice in VOICES:
            try:
                _synth_wav(voice, "Muraho.")
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
    if lang != "rw":
        return Response(status_code=400, content=f"unsupported lang '{lang}' (rw only)")
    voice = payload.get("voice") or "female"
    if voice not in VOICES:
        return Response(status_code=400, content=f"unknown voice '{voice}'")

    key = (voice, text)
    wav = _cache.get(key)
    if wav is None:
        wav = _synth_wav(voice, text)
        if len(_cache) >= _CACHE_MAX:
            _cache.pop(next(iter(_cache)))
        _cache[key] = wav
    return Response(content=wav, media_type="audio/wav")
