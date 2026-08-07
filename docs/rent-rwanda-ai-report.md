# Rent-Rwanda AI Architecture — Extraction Report

(Extracted by scout agent from /home/delta-x/rent-rwanda — patterns to reuse in Sauti.)

## Top learnings

1. **Seams for everything external/paid/non-deterministic.** LlmClient interface + real impl + scripted test double, injected via DI, overridden in tests. "AI behind an interface — the only seam the rest of the app knows."
2. **Agent grounding must be structural, not prompted.** Tools query the real DB and return safe DTOs; every surfaced entity id goes into cited_ids; at the end the server re-resolves ids against the DB — hallucinated ids vanish silently.
3. **Bounded tool loop**: MAX_STEPS = 5, accumulators (ui actions + cited ids) outside the loop, canned bilingual fallback if the model never yields text. Tools NEVER throw into the loop — errors return to the model as JSON like {"error":"..."} (class name only, no stack traces).
4. **Rate-limit anything that costs money**: per-surface caps (chat 20/window, search 30), keyed by user id when authed else first-hop X-Forwarded-For.
5. **Model choice is latency**: gpt-4o-mini default because the agent makes several calls per turn.
6. **Licensing is a launch blocker**: facebook/mms-tts-kin and XTTS are CC-BY-NC (non-commercial, unusable). DigitalUmuganda YourTTS is "cc" with unstated commercial terms — needs sign-off. Kokoro (English) is Apache-2.0 ✅. Common Voice Kinyarwanda corpus is CC0 — the clean path to training our own voice.
7. **Native-speaker review is a required acceptance gate** for any Kinyarwanda output. YourTTS was trained on Bible audio → formal register; conversational teaching wants a re-clone on a conversational speaker.
8. **Whisper cannot do Kinyarwanda** ("produced garbage"). Kinyarwanda ASR: NeMo FastConformer DigitalUmuganda/commonvoice_kinyarwanda_fastconformer (ungated, CC0 corpus). Confidence-aware routing: trust Whisper "en" only when language_probability >= 0.5, else route to FastConformer; force flags bypass. Seed Whisper's initial_prompt with domain vocabulary (for Sauti: the target lesson's vocabulary).
9. **AI features degrade gracefully** — fallback to rule-based output on blank content or any exception; voice falls back to silent text. Nothing AI-shaped may break the page it lives on.
10. **Not everything "AI" needs an LLM** — deterministic, testable rule-based logic for scoring/selection (Sauti: FSRS, placement, session building are deterministic).
11. **Prompt rules that transfer**: act first, don't interrogate; only reference DB-grounded data; don't duplicate what the UI already shows; reply in the user's language, never switch mid-conversation (TTS voice depends on it); numbers in words (text is spoken aloud); one or two short sentences; voice mode: one warm sentence, under ~30 words.
12. **Streaming voice pipeline**: SSE token stream → sentence-boundary chunking (regex on sentence enders + long clause commas) → ordered prefetching gapless TTS queue with turn-tagging for barge-in → AudioContext.resume() synchronously inside the click gesture; autoGainControl:false, echoCancellation:true; hands-free loop reads live state via refs, not React state; conversation language locked from first turn.

## The tool-calling loop (Java → Python port)

```
messages = [system(SYSTEM + (VOICE_STYLE if voice else ""))] + history + [user(msg)]
for step in range(MAX_STEPS=5):
    turn = llm.chat_stream(messages, toolbox.specs(), on_delta)
    if not turn.wants_tools(): reply = turn.content; break
    messages.append(assistant(turn.content, turn.tool_calls))
    for call in turn.tool_calls:
        result = toolbox.execute(call.name, call.arguments_json)   # never raises
        actions += result.actions; cited_ids += result.cited_ids
        messages.append(tool(call.id, result.model_json))
reply = reply or "canned bilingual fallback"
entities = service.cards_by_ids(cited_ids)   # server re-resolve: order preserved, dupes+dead ids dropped
```

- "Auto-surface" optimisation: the search tool itself emits the show-results UI action (3 steps → 2, real latency win).
- Language detection separate from model: keyword list → "rw" else "en"; used only for voice selection.
- ToolSpec = {name, description, parameters: JSON Schema} (Pydantic model_json_schema() equivalent).
- OpenAI wire quirks: tool-call deltas accumulate BY INDEX with argument string fragments concatenated; assistant tool_calls serialised as {id, type:"function", function:{name, arguments:<string>}}; tool messages carry tool_call_id.
- Error mapping: missing API key → 503 AI_UNAVAILABLE; other failures → 502 AI_ERROR.
- "One forced tool" pattern for structured extraction (single chat call, no loop; fallback to defaults if model didn't call the tool). "Graceful degradation" pattern: helper(facts, fallback) returns rule-based fallback on blank/exception.

## Auth (rotate-and-detect refresh)

- Access: HS256 JWT, 15 min, claims iss/sub/role/locale/iat/exp/jti; issuer required at parse; injectable clock; secret ≥ 32 bytes enforced at startup.
- Refresh: opaque 32 random bytes, base64url; only SHA-256 hex hash stored; 30-day TTL; family_id groups tokens from one login.
- Cookie: httpOnly, secure (config; true in prod), SameSite=Strict, path-scoped to /api/auth (only auth routes see it), maxAge; logout = same cookie maxAge 0, idempotent.
- Refresh flow: lookup by hash → not found 401 → already-revoked: revoke WHOLE family + 401 "reuse detected" → expired 401 → user inactive 403 → else revoke old, mint new in same family + new access JWT. IMPORTANT: commit the revocation before raising 401 (Spring used noRollbackFor; in SQLAlchemy commit explicitly then raise).
- Login: one generic error for unknown-email vs wrong-password; common-password denylist at register (422); rate limit register/login/refresh by client IP.
- Frontend: access token in memory only (never localStorage); credentials:"include" everywhere; on 401 → one silent refresh → retry once; on app load with cookie only → silent refresh.
- Rate limiter: in-memory fixed window ConcurrentHashMap, default 10/60s, check(key, max) per-surface overloads; note "swap for shared store when >1 node".

## Testing strategy

- Pyramid: many unit → integration on EVERY endpoint against real Postgres (Testcontainers postgres:16-alpine, one shared static container, real migrations — no in-memory DB) → a few Playwright E2E journeys.
- Test config injects: test JWT secret, cookie-secure=false, rate-limit max=1000 (override down only in the rate-limit test itself), stub providers.
- Scripted LLM idiom: the test double branches on the conversation state it is handed (e.g. count of tool messages: 0 → return tool call, else → return final text), not a call counter — this also asserts the loop appends tool results correctly. FastAPI: app.dependency_overrides[get_llm_client] = lambda: ScriptedLlm(...).
- Key assertions from their agent tests: tools execute + grounding works; protected fields never leak (jsonPath does-not-exist); SSE emits token events then done with language + entities; rate limit returns 429 after cap.
- E2E: Playwright chromium, fullyParallel, trace on-first-retry, retries 2 in CI, webServer boots dev server with env injected, runs against the REAL API with providers stubbed via config flags (not MSW). Resilience idioms: expect(a.or(b)).toBeVisible() for state-tolerant checks; Promise.all([waitForResponse, click]) to avoid racing.
- Discipline: every slice ends with green tests AND a live run against real providers.

## Voice service (already Python/FastAPI — liftable later for Sauti's speech stack)

- services/voice: assistant_app.py (port 8091: POST /tts {text,lang}→wav, POST /asr multipart→{text,language}, POST /reason), asr_kinyarwanda_app.py (port 8092, NeMo FastConformer).
- Engine interface: synth(text) -> (sample_rate, float32 mono ndarray); lazy cached_property loading; startup warm-up in daemon thread; bounded FIFO response cache (256) keyed (lang, text); soundfile → WAV bytes.
- Kinyarwanda TTS: DigitalUmuganda KinyarwandaTTS_female_voice (YourTTS/coqui, 24 kHz, ~1.4 s/sentence warm CPU). Loading gotchas: config.json has training-time absolute paths (null speakers_file/d_vector_file, write config.local.json); speakers.pth is vestigial; checkpoint name varies (best_model.pth or model.pth); pass explicit voice_dir cache + speaker_name; torch.set_num_threads(cpu_count).
- English TTS: kokoro-onnx v1.0, voice af_heart, Apache-2.0, ~0.7× realtime.
- ASR normalisation: ffmpeg -ar 16000 -ac 1 before inference; rw service unreachable → degrade to Whisper, never hard-fail.
- Venvs: Python 3.11 via uv (system 3.14 too new for torch/coqui); coqui, transformers and NeMo need SEPARATE venvs. Port 8080 often taken locally.
