# Sauti voice service (port 8093)

Thin FastAPI app exposing BOTH Kinyarwanda YourTTS voices plus an English voice,
and stitching them into one clip for mixed-language replies:

| voice    | lang | model                                        | speaker  | licence    |
|----------|------|----------------------------------------------|----------|------------|
| `female` | `rw` | DigitalUmuganda/KinyarwandaTTS_female_voice  | Diane    | as shipped |
| `male`   | `rw` | DigitalUmuganda/Kinyarwanda_YourTTS_v1       | Emmanuel | as shipped |
| —        | `en` | Kokoro v1.0 ONNX, voice `af_heart`           | —        | Apache-2.0 |

English is Kokoro, not YourTTS: Apache-2.0 is commercially safe, and it is the
same engine rent-rwanda already uses.

It imports the engine modules (`engine_yourtts.py`, `engine_kokoro.py`)
unmodified from the rent-rwanda voice service — set `VOICE_ENGINE_DIR` if that
checkout lives elsewhere (default `/home/delta-x/rent-rwanda/services/voice`).

## Run

Uses rent-rwanda's coqui venv (Python 3.11; coqui-tts pins old torch/transformers):

```sh
cd services/voice
/home/delta-x/rent-rwanda/services/voice/.venv-yourtts/bin/uvicorn tts_app:app --port 8093
```

First start downloads the male YourTTS model and the Kokoro model/voice files
(~350 MB, into `$VOICE_ENGINE_DIR/.kokoro`) and warms all three voices in a
background thread (~1–2 min). `GET /health` reports readiness per voice.

## API

- `POST /tts` `{text, lang: "rw"|"en", voice: "female"|"male"}` → `audio/wav`
  (`voice` applies to `rw` only and defaults to `female`; `en` is always
  `af_heart`). Output is each engine's native rate: 16 kHz for `rw`, 24 kHz
  for `en`.
- `POST /tts/mixed` `{segments: [{text, lang: "rw"|"en", voice?}]}` → ONE
  `audio/wav`. Empty/whitespace segments are skipped; a request with nothing
  speakable left is `400`.
- `GET /health` → `{ok: true, voices: {female: bool, male: bool, en: bool}}`

### How /tts/mixed builds one clip

Mwarimu (the study buddy) writes English with Kinyarwanda quoted inside —
*"…'Mwaramutse' means 'Good morning!'"*. Reading that in one voice mangles the
Kinyarwanda, so the API segments the reply (`sauti.speech.segmentation`) and
posts the spans here. Per span:

1. synthesize with the span's engine;
2. **resample to 24 000 Hz**, the single uniform output rate — Kokoro's native
   rate and above YourTTS's, so English is never resampled and Kinyarwanda is
   only ever upsampled;
3. **trim** leading/trailing silence (YourTTS pads ~0.6 s onto every clip; left
   in, a five-span reply gains three seconds of dead air);
4. **peak-normalize to 0.85** — the two models are trained separately and land
   at noticeably different loudness.

Spans are then joined with a **150 ms** pause and written as 16-bit PCM WAV.

Cost on CPU: roughly 3 s per English span and 4 s per Kinyarwanda span, so a
typical 3–5 span buddy reply is 8–13 s cold. Both `/tts` and `/tts/mixed` share
one bounded (256-entry) FIFO cache keyed on the exact request, so a repeat is
~60 ms — and the API keeps its own permanent Cloudinary cache in front of that.

## Wiring

Point the API at it with `VOICE_SERVICE_URL=http://127.0.0.1:8093` in the repo
root `.env` — `RealSpeechBackend` maps each item's seeded voice (Diane →
`female`, Emmanuel → `male`) for `/tts`, sends buddy replies to `/tts/mixed`,
and caches every result in Cloudinary, so each phrase is synthesized exactly
once.
