# Sauti — “Speak it as it’s spoken”

Adaptive CEFR-based language-learning platform for **Kinyarwanda, Swahili and French**.
Built from the design mockups in `design/` (`Imvugo App`, `Imvugo Class Diagram`,
`Imvugo System Design` — “Imvugo” was the design-phase working name; the product is **Sauti** — extracted text in this doc) and the patterns proven in
`/home/delta-x/rent-rwanda` (LLM seam, own-auth, e2e-first testing, voice service).

This document is the **contract** between the backend, frontend, QA and security
workstreams. If a detail is ambiguous, this doc wins; update it when a decision changes.

## 1. Product

- CEFR roadmap A1→C2 per course; each level closed by a real speaking check.
- Daily **25-minute session**: SRS due reviews + next lesson + one speaking task,
  weighted to the weakest skill.
- **Rhythm beats streaks**: consistency shown as “12 of the last 14 days” — a rest
  day never resets anything.
- Lessons teach **grammar properly** (e.g. Kinyarwanda noun classes umu-/aba-) with
  a culture note (**Umuco**) per lesson, e.g. plural forms as respect for elders.
- **Conversation practice** with personas (e.g. “Mukamana · vegetable vendor,
  Kimironko market”) — scenario goals, at most **one coach correction per turn,
  praise first** (product rule enforced server-side, not by the model).
- **Pronunciation practice**: target phrase vs learner take, per-syllable feedback
  (tone marks matter in Kinyarwanda — flat tone is “the #1 foreign tell”).
- Vocabulary organized **by situation** (market, moto, family, work…), never alphabetical;
  every word arrives inside a sentence you'd actually say.
- **Placement test**: adaptive (simple IRT), 12–18 questions, ~15 min, ends with a
  speaking sample; or “I'm brand new — start at A1”.
- Progress = **can-do statements confirmed in live speaking checks**, skill balance
  radar, pace → ETA (“at 5 h/week you reach B1 by March”).
- Week-1 vs now audio archive: keep learner recordings to show growth.
- MVP languages: **Kinyarwanda A1–A2 fully seeded**; Swahili and French courses exist
  as skeletons (course + A1 level) so the UI can list all three.

## 2. Architecture

Monorepo:

```
apps/web/        Next.js (App Router) + TypeScript + Tailwind + TanStack Query
services/api/    FastAPI (Python 3.12, async) + SQLAlchemy 2 + Pydantic v2 + Alembic
docs/            this contract + design extracts
design/          original design mockups (.dc.html)
```

- Postgres = the Supabase instance in `.env` (`POSTGRES_URL`), **all tables in a
  dedicated schema `sauti`** — the same database hosts rent-rwanda's tables in
  `public`; never touch them. Alembic manages the schema, forward-only.
- No Redis in MVP: session-plan cache and rate-limit state live in Postgres/memory
  behind small interfaces so Redis can slot in later.
- Speech models (TTS/STT/scorer) are **not** in MVP: `SpeechGateway` is a façade with
  a deterministic stub backend. Endpoint shapes are final so real model servers
  (YourTTS for Kinyarwanda per rent-rwanda, Kokoro/off-the-shelf for French) swap in
  without client changes.
- LLM via `LlmClient` seam: OpenAI `gpt-4o-mini` in prod, `FakeLlmClient` in tests.
  Same pattern as rent-rwanda's Umufasha: the model only sees tool-resolved,
  DB-grounded data and CEFR-capped prompts.

Ports: API **8000**, web **3000** (rent-rwanda uses 8080/3000 — don't clash on 8080).

## 3. Domain model (schema `sauti`)

Every entity: `id: UUID pk`, `created_at`, `updated_at`. Value objects stored as JSONB.
Aggregates are transaction boundaries.

**Curriculum**: `courses (code KIN|SWA|FRA, name)` → `levels (cefr A1..C2, title, ord)`
→ `units (title, situation_tag, ord)` → `lessons (title, ord, grammar_md, culture_note?)`
→ `items (sentence, gloss, phoneme_ref jsonb, tags text[], audio_ref?, voice_id?)`.
Plus `voices (speaker, region, consent_ref, model_version)` and
`cando (cefr, skill, text)` linked to levels.

**Learner**: `users (email unique, password_hash)` 1–1 `profiles (course_id,
pace_hours_week, placed_level?, gamification light|structured)`;
`attempts (user, item, mode read|listen|speak|write, score float 0..1, audio_ref?,
pron jsonb?, ts)`; `srs_state (user, item, due_at, reps, stability, difficulty)` —
FSRS parameters; `cando_status (user, cando, status learning|confirmed,
confirmed_via_attempt?)`; `placement_sessions (user, theta, served uuid[], result?)`.

**Conversation**: `scenarios (title, setting, persona jsonb, goals text[], min_cefr,
voice_id)`; `conversations (user, scenario, goals_met text[], started_at)`;
`messages (conversation, role user|persona|coach, text, gloss?, coach jsonb?,
audio_ref?)`.

**Auth**: `refresh_tokens (user, token_hash, expires_at, revoked_at?, replaced_by?)` —
rotation chain, reuse detection revokes the family.

Value objects (Pydantic, JSONB): `CoachNote {title, body, kind fix|praise|culture}`,
`PronReport {overall 0..100, phonemes: [{phoneme, score, note?}], tone_flags: []}`,
`SessionPlan {blocks: [{tag, mins, title, sub, kind review|lesson|speak, ref_id}],
total_min ≈ 25}`.

## 4. Service layer (plain classes, wired with Depends(), no framework in domain)

- `SessionBuilder.build_today(user) -> SessionPlan` — SRS due items + next lesson
  from roadmap position + one speaking task weighted to weakest skill.
- `SrsScheduler` — FSRS: `due_items(user, n)`, `apply(state, grade) -> SrsState`
  (pure functions; grade 1–4 again/hard/good/easy).
- `ProgressService` — `record(attempt)`, `skill_estimates(user)`, `eta_to(user, cefr)`,
  writes `cando_status` confirmations when a speaking attempt over threshold covers a can-do.
- `PlacementEngine` — `start`, `answer` (adaptive theta update, simple IRT: step theta
  by ±k/(1+n) on right/wrong, serve item nearest theta), `finalize -> CEFR`.
- `ConversationOrchestrator` — WS loop: persona + CEFR-capped system prompt → LLM →
  `CoachPolicy.evaluate` (≤1 correction/turn, praise first, culture notes) → optional
  TTS via gateway → message persisted.
- `SpeechGateway` — `tts(text, voice) -> ref`, `stt(audio, lang) -> str`,
  `score(audio, item) -> PronReport`. Only class that knows backend/model names.
  MVP backend: deterministic stub (hash-seeded scores so e2e is stable).
- `LlmClient` interface: `complete(messages, tools?) -> LlmTurn`. Impl: OpenAI
  gpt-4o-mini. Tests: `FakeLlmClient` with scripted turns.

## 5. API surface (`/api/v1`, JWT bearer; refresh via httpOnly cookie)

```
POST /auth/register {email, password, course_code, pace_hours_week}
POST /auth/login {email, password} -> {access_token, user} + Set-Cookie refresh
POST /auth/refresh -> rotates cookie, new access token
POST /auth/logout -> revokes refresh family
GET  /me -> user + profile
GET  /session/today -> SessionPlan
GET  /roadmap -> levels/units/lessons with per-user status + ETA
GET  /progress -> skill estimates, can-do list + confirmed counts, consistency, totals
GET  /vocab/decks -> situation decks with due counts; GET /vocab/decks/{tag} -> items
POST /attempts {item_id, mode, score|answer, audio_ref?} -> updated SrsState (+pron for speak)
POST /speech/upload-url {content_type} -> {upload_url, audio_ref}   (MVP: local storage)
POST /speech/score {item_id, audio_ref} -> PronReport
GET  /tts/{item_id} -> 302 to audio (MVP: stub/silence file, shape final)
GET  /scenarios -> conversation scenarios for user level
WS   /ws/conversation/{scenario_id}  client sends {text} or {audio_ref};
     server streams {type: partner|coach|goal|error, text, gloss?, coach?, audio_url?}
POST /placement/start -> {session_id, first question}
POST /placement/answer {session_id, item_id, answer} -> next question | {result, placed_level}
GET  /courses -> the three courses with availability
GET  /healthz
```

Errors: RFC7807-ish `{code, message, detail?}`; 401 on expired access (client refreshes
and retries once — TanStack Query wrapper).

## 6. Frontend screens (from the App mockup — keep its voice and copy style)

1. **Home / Today** — “Mwaramutse, Ange.” greeting, Start session (3 blocks ≈25 min),
   where-you-are card (level·unit, pace → ETA), consistency 12-of-14-days card,
   proverb of the day (“Buhoro buhoro ni rwo rugendo”), voice credit chip (“● DIANE ·
   KIGALI VOICE”).
2. **Roadmap** — six CEFR stages, units per level with done/current marks, placement CTA.
3. **Lesson player** — grammar explainer with tables (umu-/aba- noun-class table),
   “Hear it used” example rows with audio, UMUCO culture note block, quick check
   (MCQ) with feedback, “Practice these words →”.
4. **Conversation practice** — scenario header (Kimironko market run + goals),
   persona card (Mukamana), umuco tip, chat with gloss toggles, COACH notes inline,
   “Stuck? Try:” hint chips, text send + hold-to-talk mic.
5. **Pronunciation practice** — target phrase, native vs your-take waveform glyphs,
   big score, per-syllable “what to fix” chips (tone rise on KU, tapped r), record
   take N, listen slowed down.
6. **Listening** — audio player (two native voices), comprehension MCQ,
   transcript reveal (listen once first), KY/EN lines.
7. **Vocabulary** — situation decks with mastery %, due counts, “Review 8 due · 5 min”,
   sample sentence per deck.
8. **Progress** — road to B1, skill balance bars with per-skill CEFR, can-do checklist
   (“18 of 31 confirmed in live speaking checks”), week-1-vs-now recordings,
   totals (hours, weekly average, sentences spoken).
9. **Placement** — intro (12–18 questions, ~15 min, includes speaking), adaptive MCQ
   flow, “I'm brand new — start at A1” escape hatch.
10. **Auth** — register (choose course + weekly pace), login.

Language switcher shows Ikinyarwanda active, Kiswahili/Français as “+” (joinable).

## 7. Testing (user directive: **e2e over unit — e2e is the priority**)

- **Playwright e2e** against the real stack (web + api + seeded Postgres schema,
  `FakeLlmClient` + stub speech via env flag `SAUTI_FAKE_AI=1`): register→placement→
  session→lesson→review→conversation→progress. These are the acceptance bar.
- Backend: pytest — unit for FSRS/placement/coach-policy pure logic; API integration
  tests via httpx AsyncClient with test doubles for OpenAI (never call paid APIs in
  tests — rent-rwanda rule).
- Frontend: Vitest for non-trivial logic (session plan rendering, SRS grade mapping,
  API client refresh-retry).
- External/paid dependencies never run in tests; a live run proves the real one.

## 8. Security baseline

- `.env` is git-ignored; `.env.example` is the template. The current `.env` values
  were shared in chat → **rotate** (Supabase password, OpenAI key, SMTP app password,
  Cloudinary) — tracked as a security-advisory finding.
- Access JWT ~15 min; refresh = rotating opaque token, httpOnly+SameSite=Lax+Secure
  cookie, hashed at rest, family revocation on reuse.
- Passwords: bcrypt (or argon2). Rate-limit auth + LLM endpoints. CORS: frontend
  origin only. Pydantic validation everywhere; SQLAlchemy bound params only.
- LLM: system prompt treats user text as data; coach output is schema-validated
  JSON; the model can only reference curriculum items resolved from the DB.

## 9. Build order (design's M1–M2 = this MVP)

1. Scaffold + auth + curriculum tree + seed (KIN A1–A2).
2. Lesson player + attempts + FSRS reviews + session builder.
3. Placement, progress/can-do, vocab decks.
4. Conversation over WS with one scenario pack (Kimironko market) + coach policy.
5. Speech endpoints stubbed (shape-final), pronunciation UI on stub scores.
6. E2e suite green → security review → fixes.
