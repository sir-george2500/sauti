# Backend notes — services/api

Decisions, contract details and (few) deviations. The API conforms to
`docs/SPEC.md` §5 and to the frontend's DTO file
`apps/web/src/lib/api/types.ts` / `docs/frontend-notes.md`. Where the two left
room, the frontend's reading won.

## Running

```bash
cd services/api
uv sync                          # Python 3.12 pinned via .python-version
uv run alembic upgrade head      # migrates schema `sauti` on POSTGRES_URL (.env)
uv run python -m sauti.seed      # idempotent — safe to re-run
uv run uvicorn sauti.main:app --port 8000
uv run pytest                    # needs Docker (testcontainers postgres:16-alpine)
```

Config comes from the repo-root `.env` (process env wins). `SAUTI_FAKE_AI=1`
forces the scripted `FakeLlmClient` (used by e2e); tests always use it.

## Contract points the frontend should rely on

- **GET /roadmap embeds full lesson payloads** (grammar_md, culture_note,
  items with `phoneme_ref`, and a server-generated deterministic
  `quick_check`). There is no `GET /lessons/{id}`.
- **POST /attempts** returns the flattened updated SrsState
  `{item_id, due_at, reps, stability, difficulty, pron?}` plus an extra
  `confirmed_candos: uuid[]` field (safe to ignore). Grade recovery is exactly
  `grade = 1 + round(score * 3)`. A `speak` attempt with `audio_ref` always
  computes and returns `pron` (deterministic stub).
- **Speak can-do confirmation rule**: a speak attempt with score ≥ 0.8 confirms
  the *next unconfirmed* speak-skill can-do of the item's level (one per
  attempt), recording `confirmed_via_attempt`.
- **Skill labels** in `/progress` and can-dos are full words (`speaking`,
  `listening`, `reading`, `writing`); DB stores the SPEC short forms.
  `gram`/`vocab` estimates exist server-side (derived views over attempts) but
  only the four core skills are returned, per the frontend type.
- **SessionPlan.ref_id is a string**: review block → situation deck tag
  (`/vocab/{tag}`, deck with most due items), lesson → lesson UUID,
  speak → item UUID.
- **WS** `/api/v1/ws/conversation/{scenario_id}?token=<access JWT>`. Close
  codes: 4401 bad token, 4404 unknown scenario. `{audio_ref}` frames run
  through the stub STT (returns a canned Kinyarwanda line — `stub:mic-take`
  is fine). Frames stream in order: `partner` (with absolute `audio_url`),
  then `goal` per goal met, then `coach` notes (praise first, ≤1 fix,
  fixes never on the learner's first turn).
- **Public (no Authorization header)**: `GET /tts/{item_id}` (302 →
  `/api/v1/speech/audio/{ref}`), `GET /api/v1/speech/audio/{ref}`, and
  `PUT` to the returned `upload_url` (unguessable ref = signed-URL stand-in).
  CORS allows PUT from `http://localhost:3000`.
- **POST /auth/register** → 201 `{user}` — no tokens (login after).
  Refresh cookie: `sauti_refresh`, httpOnly, SameSite=Lax, path
  `/api/v1/auth`, `Secure` off in dev (config).
- Unplaced profiles behave as A1 everywhere (`placed_level: null`).
- `GET /healthz` exists both at root and under `/api/v1`.

## Deviations / interpretations

- SPEC's placement "ends with a speaking sample" is not in the §5 API; flow is
  MCQ-only (12–18 questions, adaptive theta ±K/(1+n), item nearest theta,
  result clamped to levels that actually have content — so KIN places A1/A2).
- SPEC §5 shows `GET /healthz` inside `/api/v1`; also exposed at root for
  infra probes.
- `available` on a course = it has ≥30 items (KIN true; SWA/FRA skeletons
  false).
- Consistency = distinct UTC days with ≥1 attempt in the last 14.
  Totals hours are estimated at 0.75 min/attempt; ETA assumes 0.4 h per
  remaining lesson at the profile's `pace_hours_week`, target = one CEFR past
  the last seeded level (B1 for KIN).
- FSRS is FSRS-4.5 with default weights; grade 1 re-serves in 10 minutes;
  intervals capped at 365 d; desired retention 0.9 (interval ≈ stability).

## Security notes

- rent-rwanda auth pattern implemented fully: HS256 access JWT 15 min (iss
  required, secret ≥32 bytes enforced at startup), opaque 32-byte refresh
  tokens stored as SHA-256, family rotation, reuse detection revokes the whole
  family and **commits before raising 401**; generic login error; common-
  password denylist at register; fixed-window in-memory rate limiter (auth
  10/60 s, conversation 20/60 s) keyed by user id / first-hop XFF.
- Supabase is shared with rent-rwanda (`public` schema): everything lives in
  schema `sauti`; Alembic pins `version_table_schema="sauti"` and filters
  `include_name` so autogenerate can never see or touch other schemas.
- The Supabase pooler (pgbouncer, transaction mode, port 6543) requires
  asyncpg's prepared-statement cache disabled — done in `sauti.db`.
  `sslmode=require` is honoured as encrypt-without-verify (pooler chain is
  self-signed).
- SPEC §8's credential rotation (Supabase/OpenAI/SMTP values shared in chat)
  is still owed — flagged for the security workstream.

## Tests

`uv run pytest` → **91 passed** (41 unit / 50 integration; no skips).
Integration runs against a real postgres:16-alpine testcontainer with real
Alembic migrations + real seed; `FakeLlmClient` scripted per the rent-rwanda
idiom (branches on conversation state, not call counts). No paid API is ever
called in tests.
