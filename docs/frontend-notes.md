# Frontend notes — decisions & spec ambiguities (apps/web)

Where SPEC.md §5 leaves a shape open, the frontend chose the simplest reading.
All DTO shapes live in one file: `apps/web/src/lib/api/types.ts`. If the
backend lands a different shape, update that file + this list together.

## Missing endpoints worked around (no endpoints invented)

1. **No lesson-detail endpoint.** §6 requires a lesson player but §5 has no
   `GET /lessons/{id}`. Chosen reading: `GET /roadmap` embeds full lesson
   payloads — each lesson carries `grammar_md`, `culture_note`, `items[]`
   (sentence, gloss, audio) and a `quick_check {question, options[{text,
   correct}]}`. The lookup is isolated in `getLesson()` in
   `src/lib/api/endpoints.ts`; if the backend prefers a dedicated endpoint,
   only that function changes.
2. **No item-detail endpoint.** The pronunciation screen (`/practice/
   pronunciation/[itemId]`) resolves its target phrase by scanning the
   roadmap's embedded lesson items (`findItem()` in `endpoints.ts`). Same
   swap-point as above.
3. **No proverb endpoint.** Proverb of the day rotates a curated client-side
   list by day of year (`src/lib/proverbs.ts`).
4. **No hint endpoint.** The conversation "Stuck? Try:" chips are a static
   phrase list appropriate to the market scenario.

## Backend additions (2026-08)

- **`items[].audio_url`** (roadmap embedded lessons AND `/vocab/decks/{tag}`):
  the cached Cloudinary TTS URL, playable directly as an `<audio>` src — no
  `GET /tts/{item_id}` round trip. `null` when not yet cached; fall back to
  the `/tts` route then. Resolved server-side with one bulk query per request.
- **`lesson.quiz`**: 4–6 questions per KIN lesson —
  `[{ord, kind: "grammar"|"vocab"|"usage"|"culture", question,
  options: [{text, correct}], explanation, item_id?}]`. `explanation` is the
  one-sentence WHY to show after answering. Post one attempt per question
  (`mode: "read"`, score 1/0) against `item_id`, or the lesson's first item
  when `item_id` is null. `quick_check` remains populated (it mirrors
  `quiz[0]`) for rollout compatibility; skeleton courses (SWA/FRA) have
  `quiz: []` and keep the derived quick_check.

## Shape choices within §5

- **`POST /attempts` response** is read as the updated `SrsState` itself with
  an optional `pron` field for speak attempts (`AttemptResponse extends
  SrsState`), i.e. `{item_id, due_at, reps, stability, difficulty, pron?}`.
- **SRS grades → score**: the attempts endpoint takes `score` (0..1), not a
  grade, so again/hard/good/easy (FSRS 1–4) map to evenly spaced scores
  0, 1/3, 2/3, 1. Backend can recover the grade exactly as
  `grade = 1 + round(score * 3)` (unit-tested in `src/lib/srs.test.ts`).
  SRS reviews are sent with `mode: "read"`.
- **Lesson quick-check** answers are also posted as attempts (`mode: "read"`,
  score 1/0) against the lesson's first item so the item feeds SRS.
- **Pronunciation flow**: `POST /speech/upload-url` → `PUT` blob to
  `upload_url` → `POST /speech/score` renders the `PronReport`; additionally a
  `mode: "speak"` attempt (`score = overall/100`, `audio_ref`) is posted so
  progress totals and can-do confirmations move.
- **`GET /roadmap`** expected shape: `{course_code, levels[], eta?, current?}`
  with `status: done|current|available|locked` on levels/units/lessons;
  `eta = {target_cefr, eta_date, pace_hours_week}`;
  `current = {cefr, unit_title, unit_ord?, lesson_id?}` (drives the Today
  "Where you are" card).
- **`GET /progress`** expected shape:
  `{skills[{skill, cefr, pct 0..1}], cando{items[], confirmed, total},
  consistency{active_days, window_days}, totals{hours_total,
  weekly_avg_hours, sentences_spoken}, eta?}`.
- **`GET /vocab/decks`** → `{decks[{tag, title, gloss, word_count,
  mastery 0..1, due_count, sample?{sentence, gloss}}], total_due}`;
  `GET /vocab/decks/{tag}` → `{tag, title, items[]}`.
- **`GET /courses`** → `Course[]` (`{id, code, name, available}`).
- **`GET /scenarios`** → `Scenario[]`; there is no per-scenario GET, so the
  conversation page finds its scenario in the list. Persona JSONB is read as
  `{name, role, description?}` plus optional `umuco_tip` on the scenario.
- **Placement**: `POST /placement/start` → `{session_id, question}`;
  question = `{item_id, prompt, options: string[], number?, total?}`; the
  submitted `answer` is the chosen option string. `POST /placement/answer`
  returns either `{question}` or `{result, placed_level}` (discriminated by
  `placed_level`). The spec's "ends with a speaking sample" is not in the §5
  placement API, so the MVP flow is MCQ-only.
- **"I'm brand new — start at A1"** has no endpoint; it simply routes home and
  relies on the backend defaulting an unplaced profile to A1.
- **`POST /auth/register`** is not assumed to return tokens; the client
  registers then logs in with the same credentials.
- **WebSocket**: URL is `ws(s)://…/api/v1/ws/conversation/{scenario_id}` (the
  WS route is listed inside the §5 `/api/v1` surface). The access token is
  passed as a `?token=` query param since browsers can't set WS headers —
  backend needs to accept that (or an initial auth frame; happy to change).
  The mic is a stub per §2: it records via MediaRecorder but sends
  `{audio_ref: "stub:mic-take"}`.
- **`GET /tts/{item_id}`** is used directly as an `<audio>`/`Audio` `src`, so
  it must be reachable without an `Authorization` header (cookie or public in
  MVP) — an audio element can't send a bearer token.
- **Study buddy (Mwarimu)**: `ws(s)://…/api/v1/ws/buddy?token=…`, client sends
  `{text}` (capped at 500 chars client-side, truncated again server-side).
  Server frames: `{type:"buddy", id?, text, gloss?}`, `{type:"buddy_audio",
  id, audio_url}`, `{type:"action", action:
  {kind:"navigate", href, label}}`, `{type:"error", text}`. The widget mounts
  once in `AppShell` (inside `RequireAuth`), so it exists on every authenticated
  route and on none of the auth pages. Conversation state lives in
  `src/lib/buddy/store.ts` (module store + sessionStorage, wiped on sign-out);
  the socket connects on first open, reconnects with bounded backoff after a
  drop, and closes after 3 idle minutes with the panel shut. Action hrefs are
  re-checked client-side by `safeAppHref()` — only in-app absolute paths are
  followed, the same open-redirect rule as the login `?next=` param.
- **Mwarimu's voice**: a buddy frame carrying an `id` means a clip is being
  synthesized; the matching `buddy_audio` frame attaches it to that turn (by
  id — an unmatched or malformed frame is dropped). Each such turn shows
  `buddy-play` with `data-state=pending|ready|playing`; a clip that never
  arrives simply stays pending, because a voice service that is down is a
  silent degradation, not an error. `buddy-sound-toggle` (`data-on`) is the
  speaker, persisted in `localStorage["sauti.buddy.sound.v1"]`, default ON:
  with it on, the NEWEST reply plays itself once, and blocked autoplay
  (`audio.play()` rejects) silently falls back to the ready button. Clip URLs
  are guarded by `safeAudioUrl()` (http(s) or same-origin path only), and all
  playback runs through `src/lib/audio/player.ts` — one clip at a time app-wide,
  stopped when the panel closes, on mute, or on a guidance-chip navigation.
- **Listening practice** is lesson-based (`/practice/listening/[lessonId]`):
  the lesson's items are the dialogue lines/transcript and its `quick_check`
  doubles as the comprehension MCQ (no dedicated listening payload in §5).

## For QA (Playwright)

Stable `data-testid`s on all interactive elements and landmarks, including:
`start-session`, `session-block`, `greeting`, `where-you-are`, `consistency`,
`proverb-card`, `placement-cta`, `roadmap-level-{CEFR}`, `roadmap-unit`,
`grammar-md`, `example-row`, `play-audio`, `umuco-note`, `quick-check`,
`quick-check-option`, `mcq-feedback`, `practice-words`, `persona-card`,
`umuco-tip`, `chat-input`, `chat-send`, `mic-button`, `hint-chip`,
`partner-message`, `user-message`, `coach-note`, `gloss-toggle`, `goal`,
`target-phrase`, `play-native`, `play-slow`, `record-button`, `pron-score`,
`phoneme-chip`, `tone-flag`, `listening-play`, `comprehension-option`,
`transcript-toggle`, `transcript`, `vocab-deck`, `review-due`, `reveal-card`,
`grade-again|hard|good|easy`, `review-done`, `skill-{skill}`, `cando-item`,
`cando-count`, `begin-placement`, `start-at-a1`, `placement-answer`,
`placement-submit`, `placement-result`, `login-*`, `register-*`,
`buddy-fab`, `buddy-panel`, `buddy-close`, `buddy-messages`, `buddy-message`
(with `data-role="learner|buddy"`), `buddy-gloss`, `buddy-typing`,
`buddy-action` (with `data-href`), `buddy-opener`, `buddy-input`, `buddy-send`,
`buddy-play` (with `data-state="pending|ready|playing"`), `buddy-sound-toggle`
(with `data-on`),
`course-{CODE}`, `pace-{hours}`, `sign-out`, `nav-*`.
