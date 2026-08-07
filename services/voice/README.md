# Sauti voice service (port 8093)

Thin FastAPI app exposing BOTH Kinyarwanda YourTTS voices:

| voice    | model                                        | speaker |
|----------|----------------------------------------------|---------|
| `female` | DigitalUmuganda/KinyarwandaTTS_female_voice  | Diane   |
| `male`   | DigitalUmuganda/Kinyarwanda_YourTTS_v1       | Emmanuel |

It imports the engine modules (`engine_yourtts.py` etc.) unmodified from the
rent-rwanda voice service — set `VOICE_ENGINE_DIR` if that checkout lives
elsewhere (default `/home/delta-x/rent-rwanda/services/voice`).

## Run

Uses rent-rwanda's coqui venv (Python 3.11; coqui-tts pins old torch/transformers):

```sh
cd services/voice
/home/delta-x/rent-rwanda/services/voice/.venv-yourtts/bin/uvicorn tts_app:app --port 8093
```

First start downloads the male model from Hugging Face and warms both voices in
a background thread (~1–2 min). `GET /health` reports readiness per voice.

## API

- `POST /tts` `{text, lang: "rw", voice: "female"|"male"}` → `audio/wav`
  (`voice` defaults to `female`; only Kinyarwanda is served here)
- `GET /health` → `{ok: true, voices: {female: bool, male: bool}}`

Point the API at it with `VOICE_SERVICE_URL=http://127.0.0.1:8093` in the repo
root `.env` — the RealSpeechBackend maps each item's seeded voice
(Diane → `female`, Emmanuel → `male`) and caches synthesized audio in
Cloudinary, so each phrase is synthesized exactly once.
