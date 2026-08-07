/**
 * Shared DTO types for the Sauti API — the single source of truth on the
 * frontend for the shapes in docs/SPEC.md §3 (value objects) and §5 (API
 * surface). Where the spec is ambiguous the simplest reading was chosen and
 * recorded in docs/frontend-notes.md.
 */

export type CourseCode = "KIN" | "SWA" | "FRA";
export type Cefr = "A1" | "A2" | "B1" | "B2" | "C1" | "C2";
export type Skill = "listening" | "speaking" | "reading" | "writing";
export type AttemptMode = "read" | "listen" | "speak" | "write";

// ---------------------------------------------------------------------------
// Auth / me
// ---------------------------------------------------------------------------

export interface User {
  id: string;
  email: string;
}

export interface Profile {
  course_id: string;
  course_code?: CourseCode;
  pace_hours_week: number;
  placed_level?: Cefr | null;
  gamification?: "light" | "structured";
  display_name?: string | null;
}

export interface RegisterRequest {
  email: string;
  password: string;
  course_code: CourseCode;
  pace_hours_week: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

/** POST /auth/login and /auth/refresh both yield a fresh access token. */
export interface AuthResponse {
  access_token: string;
  user: User;
}

/** GET /me -> user + profile */
export interface MeResponse {
  user: User;
  profile: Profile;
}

// ---------------------------------------------------------------------------
// Courses
// ---------------------------------------------------------------------------

export interface Course {
  id: string;
  code: CourseCode;
  name: string;
  available: boolean;
}

// ---------------------------------------------------------------------------
// Session plan (SPEC §3 value object)
// ---------------------------------------------------------------------------

export type SessionBlockKind = "review" | "lesson" | "speak";

export interface SessionBlock {
  tag: string;
  mins: number;
  title: string;
  sub: string;
  kind: SessionBlockKind;
  ref_id: string;
}

export interface SessionPlan {
  blocks: SessionBlock[];
  total_min: number;
}

// ---------------------------------------------------------------------------
// Roadmap
// ---------------------------------------------------------------------------

export type RoadmapStatus = "done" | "current" | "available" | "locked";

/** Curriculum item (SPEC §3): a sentence you'd actually say. */
export interface Item {
  id: string;
  sentence: string;
  gloss: string;
  tags?: string[];
  audio_ref?: string | null;
  voice_id?: string | null;
}

export interface QuickCheckOption {
  text: string;
  correct: boolean;
}

export interface QuickCheck {
  question: string;
  options: QuickCheckOption[];
}

/**
 * Lesson as embedded in GET /roadmap. SPEC §5 has no dedicated lesson-detail
 * endpoint, so the roadmap payload is expected to carry lesson content
 * (grammar_md, culture_note, items, quick_check) — see docs/frontend-notes.md.
 */
export interface RoadmapLesson {
  id: string;
  title: string;
  ord: number;
  status: RoadmapStatus;
  grammar_md?: string | null;
  culture_note?: string | null;
  items?: Item[];
  quick_check?: QuickCheck | null;
}

export interface RoadmapUnit {
  id: string;
  title: string;
  situation_tag: string;
  ord: number;
  status: RoadmapStatus;
  lessons: RoadmapLesson[];
}

export interface RoadmapLevel {
  cefr: Cefr;
  title: string;
  ord: number;
  status: RoadmapStatus;
  units: RoadmapUnit[];
}

export interface RoadmapEta {
  target_cefr: Cefr;
  eta_date: string; // ISO date
  pace_hours_week: number;
}

export interface RoadmapResponse {
  course_code: CourseCode;
  levels: RoadmapLevel[];
  eta?: RoadmapEta | null;
  current?: {
    cefr: Cefr;
    unit_title: string;
    unit_ord?: number;
    lesson_id?: string | null;
    lesson_ord?: number;
  } | null;
}

// ---------------------------------------------------------------------------
// Progress
// ---------------------------------------------------------------------------

export interface SkillEstimate {
  skill: Skill;
  cefr: Cefr;
  /** 0..1 progress within the current CEFR band. */
  pct: number;
}

export interface CanDo {
  id: string;
  cefr: Cefr;
  skill: Skill;
  text: string;
  status: "learning" | "confirmed";
}

export interface Consistency {
  active_days: number;
  window_days: number;
}

export interface ProgressTotals {
  hours_total: number;
  weekly_avg_hours: number;
  sentences_spoken: number;
}

export interface ProgressResponse {
  skills: SkillEstimate[];
  cando: {
    items: CanDo[];
    confirmed: number;
    total: number;
  };
  consistency: Consistency;
  totals: ProgressTotals;
  eta?: RoadmapEta | null;
}

// ---------------------------------------------------------------------------
// Vocab / SRS
// ---------------------------------------------------------------------------

export interface VocabDeck {
  tag: string;
  title: string;
  gloss: string;
  word_count: number;
  /** 0..1 mastery across the deck. */
  mastery: number;
  due_count: number;
  sample?: {
    sentence: string;
    gloss: string;
  } | null;
}

export interface VocabDecksResponse {
  decks: VocabDeck[];
  total_due: number;
}

export interface VocabDeckItemsResponse {
  tag: string;
  title: string;
  items: Item[];
}

/** SRS grade 1–4: again / hard / good / easy (SPEC §4 SrsScheduler). */
export type SrsGrade = 1 | 2 | 3 | 4;
export type SrsGradeLabel = "again" | "hard" | "good" | "easy";

export interface AttemptRequest {
  item_id: string;
  mode: AttemptMode;
  score?: number;
  answer?: string;
  audio_ref?: string;
}

export interface SrsState {
  item_id: string;
  due_at: string; // ISO datetime
  reps: number;
  stability: number;
  difficulty: number;
}

/** POST /attempts -> updated SrsState (+pron for speak attempts). */
export interface AttemptResponse extends SrsState {
  pron?: PronReport | null;
}

// ---------------------------------------------------------------------------
// Speech (SPEC §3 PronReport, §5 speech endpoints)
// ---------------------------------------------------------------------------

export interface PronPhoneme {
  phoneme: string;
  score: number; // 0..100
  note?: string | null;
}

export interface PronReport {
  overall: number; // 0..100
  phonemes: PronPhoneme[];
  tone_flags: string[];
  /** What the recognizer heard — rendered as "We heard: …". */
  transcript?: string | null;
}

export interface UploadUrlRequest {
  content_type: string;
}

export interface UploadUrlResponse {
  upload_url: string;
  audio_ref: string;
}

export interface SpeechScoreRequest {
  item_id: string;
  audio_ref: string;
}

// ---------------------------------------------------------------------------
// Conversation
// ---------------------------------------------------------------------------

export interface Persona {
  name: string;
  role: string;
  description?: string | null;
}

export interface Scenario {
  id: string;
  title: string;
  setting: string;
  persona: Persona;
  goals: string[];
  min_cefr: Cefr;
  voice_id?: string | null;
  umuco_tip?: string | null;
}

/** SPEC §3 CoachNote value object. */
export interface CoachNote {
  title: string;
  body: string;
  kind: "fix" | "praise" | "culture";
}

/** Client -> server over WS /ws/conversation/{scenario_id}. */
export interface ConversationClientMessage {
  text?: string;
  audio_ref?: string;
}

/**
 * Server -> client stream frames. With the real speech backend the partner
 * frame arrives text-first (audio_url null) and a follow-up
 * {type: "partner_audio", audio_url} frame carries the synthesized audio once
 * ready; the stub backend keeps audio_url inline on the partner frame.
 */
export interface ConversationServerMessage {
  type: "partner" | "coach" | "goal" | "error" | "partner_audio";
  text: string;
  gloss?: string | null;
  coach?: CoachNote | null;
  audio_url?: string | null;
}

// ---------------------------------------------------------------------------
// Placement
// ---------------------------------------------------------------------------

export interface PlacementQuestion {
  item_id: string;
  prompt: string;
  options: string[];
  /** 1-based position, when the server provides it. */
  number?: number;
  total?: number;
}

export interface PlacementStartResponse {
  session_id: string;
  question: PlacementQuestion;
}

export interface PlacementAnswerRequest {
  session_id: string;
  item_id: string;
  answer: string;
}

/** Either the next question, or the final result with a placed level. */
export interface PlacementAnswerResponse {
  question?: PlacementQuestion | null;
  result?: string | null;
  placed_level?: Cefr | null;
}

// ---------------------------------------------------------------------------
// Errors (RFC7807-ish)
// ---------------------------------------------------------------------------

export interface ApiErrorBody {
  code: string;
  message: string;
  detail?: unknown;
}
