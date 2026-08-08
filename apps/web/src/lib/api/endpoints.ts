import { apiFetch, setAccessToken } from "./client";
import type {
  AttemptRequest,
  AttemptResponse,
  AuthResponse,
  Course,
  Item,
  LoginRequest,
  MeResponse,
  NotebookCreateRequest,
  NotebookEntry,
  NotebookUpdateRequest,
  OkResponse,
  PlacementAnswerRequest,
  PlacementAnswerResponse,
  PlacementStartResponse,
  Profile,
  ProfilePatchRequest,
  ProgressResponse,
  PronReport,
  Recording,
  RegisterRequest,
  RoadmapLesson,
  RoadmapLevel,
  RoadmapResponse,
  RoadmapStatus,
  RoadmapUnit,
  Scenario,
  SessionPlan,
  SpeechScoreRequest,
  UploadUrlRequest,
  UploadUrlResponse,
  VocabDeckItemsResponse,
  VocabDecksResponse,
} from "./types";

// --- Auth -------------------------------------------------------------------

export async function register(body: RegisterRequest): Promise<void> {
  await apiFetch<unknown>("/auth/register", { method: "POST", body });
}

export async function login(body: LoginRequest): Promise<AuthResponse> {
  const res = await apiFetch<AuthResponse>("/auth/login", { method: "POST", body });
  setAccessToken(res.access_token);
  return res;
}

export async function logout(): Promise<void> {
  try {
    await apiFetch<unknown>("/auth/logout", { method: "POST" });
  } finally {
    setAccessToken(null);
  }
}

export const getMe = () => apiFetch<MeResponse>("/me");

export const verifyEmail = (token: string) =>
  apiFetch<OkResponse>("/auth/verify-email", { method: "POST", body: { token } });

/** Auth'd; the API answers a generic 200 even when already verified. */
export const resendVerification = () =>
  apiFetch<OkResponse>("/auth/resend-verification", { method: "POST" });

/** Always resolves 200 whether or not the email has an account. */
export const forgotPassword = (email: string) =>
  apiFetch<OkResponse>("/auth/forgot-password", { method: "POST", body: { email } });

export const resetPassword = (token: string, newPassword: string) =>
  apiFetch<OkResponse>("/auth/reset-password", {
    method: "POST",
    body: { token, new_password: newPassword },
  });

/** PATCH /me/profile — currently just the daily study-timer goal. */
export const patchProfile = (body: ProfilePatchRequest) =>
  apiFetch<Profile>("/me/profile", { method: "PATCH", body });

// --- Notebook (Ikaye) -------------------------------------------------------

export const getNotebook = () => apiFetch<NotebookEntry[]>("/notebook");

export const addNotebookEntry = (body: NotebookCreateRequest) =>
  apiFetch<NotebookEntry>("/notebook", { method: "POST", body });

export const updateNotebookEntry = (id: string, body: NotebookUpdateRequest) =>
  apiFetch<NotebookEntry>(`/notebook/${id}`, { method: "PATCH", body });

export const deleteNotebookEntry = (id: string) =>
  apiFetch<void>(`/notebook/${id}`, { method: "DELETE" });

// --- Content ----------------------------------------------------------------

export const getCourses = () => apiFetch<Course[]>("/courses");
export const getSessionToday = () => apiFetch<SessionPlan>("/session/today");
export const getRoadmap = () => apiFetch<RoadmapResponse>("/roadmap");
export const getProgress = () => apiFetch<ProgressResponse>("/progress");
export const getRecordings = () => apiFetch<Recording[]>("/progress/recordings");
export const getVocabDecks = () => apiFetch<VocabDecksResponse>("/vocab/decks");
export const getVocabDeck = (tag: string) =>
  apiFetch<VocabDeckItemsResponse>(`/vocab/decks/${encodeURIComponent(tag)}`);
export const getScenarios = () => apiFetch<Scenario[]>("/scenarios");

/** Neighbouring lesson in roadmap order — enough to render a nav link. */
export interface LessonNavRef {
  id: string;
  title: string;
  status: RoadmapStatus;
  /** "1.2" — unit ord, then the 1-based lesson position within that unit. */
  label: string;
}

export interface LessonView {
  lesson: RoadmapLesson;
  unitTitle: string;
  levelCefr: string;
  lessonNumber: number;
  lessonCount: number;
  /** Previous lesson in roadmap order, across unit/level boundaries. */
  prev_lesson_id: string | null;
  /** Next lesson in roadmap order, across unit/level boundaries. */
  next_lesson_id: string | null;
  prev: LessonNavRef | null;
  next: LessonNavRef | null;
}

interface FlatLesson {
  lesson: RoadmapLesson;
  unit: RoadmapUnit;
  level: RoadmapLevel;
  /** 0-based position within the unit. */
  idxInUnit: number;
}

/** All lessons in course order (payload order: levels → units → lessons). */
function flattenLessons(roadmap: RoadmapResponse): FlatLesson[] {
  const out: FlatLesson[] = [];
  for (const level of roadmap.levels) {
    for (const unit of level.units) {
      unit.lessons.forEach((lesson, idxInUnit) => out.push({ lesson, unit, level, idxInUnit }));
    }
  }
  return out;
}

function navRef(entry: FlatLesson | undefined): LessonNavRef | null {
  if (!entry) return null;
  return {
    id: entry.lesson.id,
    title: entry.lesson.title,
    status: entry.lesson.status,
    label: `${entry.unit.ord}.${entry.idxInUnit + 1}`,
  };
}

/**
 * SPEC §5 has no lesson-detail endpoint; lesson content is read out of the
 * roadmap payload (see docs/frontend-notes.md). Pure so pages can derive it
 * from the shared ["roadmap"] react-query cache instead of re-fetching the
 * (expensive) roadmap per screen. Also derives the previous/next lesson in
 * roadmap order (crossing unit and level boundaries) for revision navigation.
 */
export function lessonFromRoadmap(
  roadmap: RoadmapResponse,
  lessonId: string,
): LessonView | null {
  const flat = flattenLessons(roadmap);
  const i = flat.findIndex((e) => e.lesson.id === lessonId);
  if (i === -1) return null;
  const { lesson, unit, level, idxInUnit } = flat[i];
  const prev = navRef(flat[i - 1]);
  const next = navRef(flat[i + 1]);
  return {
    lesson,
    unitTitle: unit.title,
    levelCefr: level.cefr,
    lessonNumber: idxInUnit + 1,
    lessonCount: unit.lessons.length,
    prev_lesson_id: prev?.id ?? null,
    next_lesson_id: next?.id ?? null,
    prev,
    next,
  };
}

/** See lessonFromRoadmap — kept for callers outside a roadmap query. */
export async function getLesson(lessonId: string): Promise<LessonView | null> {
  return lessonFromRoadmap(await getRoadmap(), lessonId);
}

/**
 * SPEC §5 has no item-detail endpoint either; the pronunciation screen needs
 * the target sentence for an item id, so it is looked up from the roadmap's
 * embedded lesson items (see docs/frontend-notes.md).
 */
export function itemFromRoadmap(roadmap: RoadmapResponse, itemId: string): Item | null {
  for (const level of roadmap.levels) {
    for (const unit of level.units) {
      for (const lesson of unit.lessons) {
        const item = lesson.items?.find((i) => i.id === itemId);
        if (item) return item;
      }
    }
  }
  return null;
}

/** See itemFromRoadmap — kept for callers outside a roadmap query. */
export async function findItem(itemId: string): Promise<Item | null> {
  return itemFromRoadmap(await getRoadmap(), itemId);
}

// --- Attempts / SRS ---------------------------------------------------------

export const postAttempt = (body: AttemptRequest) =>
  apiFetch<AttemptResponse>("/attempts", { method: "POST", body });

// --- Speech -----------------------------------------------------------------

export const getUploadUrl = (body: UploadUrlRequest) =>
  apiFetch<UploadUrlResponse>("/speech/upload-url", { method: "POST", body });

export const scoreSpeech = (body: SpeechScoreRequest) =>
  apiFetch<PronReport>("/speech/score", { method: "POST", body });

/** PUT the recorded blob to the upload URL the API handed us. */
export async function uploadAudio(uploadUrl: string, blob: Blob): Promise<void> {
  const res = await fetch(uploadUrl, {
    method: "PUT",
    headers: { "Content-Type": blob.type || "application/octet-stream" },
    body: blob,
  });
  if (!res.ok) throw new Error(`Audio upload failed (${res.status})`);
}

// --- Placement --------------------------------------------------------------

export const placementStart = () =>
  apiFetch<PlacementStartResponse>("/placement/start", { method: "POST" });

export const placementAnswer = (body: PlacementAnswerRequest) =>
  apiFetch<PlacementAnswerResponse>("/placement/answer", { method: "POST", body });
