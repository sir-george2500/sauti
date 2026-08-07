import { apiFetch, setAccessToken } from "./client";
import type {
  AttemptRequest,
  AttemptResponse,
  AuthResponse,
  Course,
  Item,
  LoginRequest,
  MeResponse,
  PlacementAnswerRequest,
  PlacementAnswerResponse,
  PlacementStartResponse,
  ProgressResponse,
  PronReport,
  RegisterRequest,
  RoadmapLesson,
  RoadmapResponse,
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

// --- Content ----------------------------------------------------------------

export const getCourses = () => apiFetch<Course[]>("/courses");
export const getSessionToday = () => apiFetch<SessionPlan>("/session/today");
export const getRoadmap = () => apiFetch<RoadmapResponse>("/roadmap");
export const getProgress = () => apiFetch<ProgressResponse>("/progress");
export const getVocabDecks = () => apiFetch<VocabDecksResponse>("/vocab/decks");
export const getVocabDeck = (tag: string) =>
  apiFetch<VocabDeckItemsResponse>(`/vocab/decks/${encodeURIComponent(tag)}`);
export const getScenarios = () => apiFetch<Scenario[]>("/scenarios");

/**
 * SPEC §5 has no lesson-detail endpoint; lesson content is read out of the
 * roadmap payload (see docs/frontend-notes.md). Swap this implementation for
 * a dedicated fetch if the backend adds GET /lessons/{id}.
 */
export async function getLesson(lessonId: string): Promise<{
  lesson: RoadmapLesson;
  unitTitle: string;
  levelCefr: string;
  lessonNumber: number;
  lessonCount: number;
} | null> {
  const roadmap = await getRoadmap();
  for (const level of roadmap.levels) {
    for (const unit of level.units) {
      const idx = unit.lessons.findIndex((l) => l.id === lessonId);
      if (idx !== -1) {
        return {
          lesson: unit.lessons[idx],
          unitTitle: unit.title,
          levelCefr: level.cefr,
          lessonNumber: idx + 1,
          lessonCount: unit.lessons.length,
        };
      }
    }
  }
  return null;
}

/**
 * SPEC §5 has no item-detail endpoint either; the pronunciation screen needs
 * the target sentence for an item id, so it is looked up from the roadmap's
 * embedded lesson items (see docs/frontend-notes.md).
 */
export async function findItem(itemId: string): Promise<Item | null> {
  const roadmap = await getRoadmap();
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
