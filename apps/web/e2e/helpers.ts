import { expect, type APIRequestContext, type Page } from "@playwright/test";
import { execFileSync } from "child_process";
import path from "path";

/**
 * Shared helpers for the Sauti e2e suite.
 *
 * Tests run against the real API + a real shared Postgres (schema `sauti`),
 * so every test creates its own throwaway user (timestamp+random email) and
 * never depends on data another run left behind.
 */

export const API_BASE = "http://localhost:8000/api/v1";
export const PASSWORD = "SautiE2e!Passw0rd";

const API_DIR = path.resolve(__dirname, "../../../services/api");

export function uniqueEmail(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@e2e.sauti.dev`;
}

/** POST /auth/register — 201, no tokens (login after, per backend-notes). */
export async function apiRegister(
  request: APIRequestContext,
  email: string,
  pace = 5,
): Promise<void> {
  const res = await request.post(`${API_BASE}/auth/register`, {
    data: { email, password: PASSWORD, course_code: "KIN", pace_hours_week: pace },
  });
  expect(res.status(), await res.text()).toBe(201);
}

/**
 * POST /auth/login through the PAGE's request context: the `sauti_refresh`
 * httpOnly cookie lands in the browser context's cookie jar, so the next
 * page load bootstraps the session via the app's silent-refresh path.
 * Returns the access token for direct API calls from the test.
 */
export async function apiLogin(page: Page, email: string): Promise<string> {
  const res = await page.request.post(`${API_BASE}/auth/login`, {
    data: { email, password: PASSWORD },
  });
  expect(res.status(), await res.text()).toBe(200);
  const body = (await res.json()) as { access_token: string };
  return body.access_token;
}

/** Register + login + land on an authenticated page. */
export async function freshUser(
  page: Page,
  prefix: string,
): Promise<{ email: string; token: string }> {
  const email = uniqueEmail(prefix);
  await apiRegister(page.request, email);
  const token = await apiLogin(page, email);
  return { email, token };
}

export function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

export async function getJson<T>(
  request: APIRequestContext,
  pathname: string,
  token: string,
): Promise<T> {
  const res = await request.get(`${API_BASE}${pathname}`, {
    headers: authHeaders(token),
  });
  expect(res.status(), `${pathname}: ${await res.text()}`).toBe(200);
  return (await res.json()) as T;
}

export async function postJson<T>(
  request: APIRequestContext,
  pathname: string,
  token: string,
  data: unknown,
): Promise<T> {
  const res = await request.post(`${API_BASE}${pathname}`, {
    headers: authHeaders(token),
    data,
  });
  expect(res.status(), `${pathname}: ${await res.text()}`).toBe(200);
  return (await res.json()) as T;
}

// --- Roadmap shapes (subset the tests need) --------------------------------

export interface RoadmapItem {
  id: string;
  sentence: string;
  gloss: string;
}

export interface RoadmapPayload {
  course_code: string;
  levels: {
    cefr: string;
    units: {
      situation_tag: string;
      lessons: {
        id: string;
        title: string;
        items?: RoadmapItem[];
        quick_check?: { question: string; options: { text: string; correct: boolean }[] } | null;
      }[];
    }[];
  }[];
}

export function allItems(roadmap: RoadmapPayload): RoadmapItem[] {
  const out: RoadmapItem[] = [];
  for (const level of roadmap.levels)
    for (const unit of level.units)
      for (const lesson of unit.lessons) out.push(...(lesson.items ?? []));
  return out;
}

/**
 * FSRS never schedules an item into the past, so "due now" state cannot be
 * produced through the API alone. This test fixture rewinds the user's
 * srs_state.due_at by one hour directly in the DB (same trick a time-machine
 * clock would do), via the API project's own Python env + settings.
 */
export function rewindSrsDue(email: string): number {
  const script = path.join(__dirname, "helpers", "rewind_srs_due.py");
  const out = execFileSync("uv", ["run", "python", script, email], {
    cwd: API_DIR,
    encoding: "utf-8",
    env: {
      ...process.env,
      // The suite runs against the disposable local e2e Postgres (see
      // scripts/e2e-db.sh + playwright.config.ts webServer), not the remote
      // dev DB from .env — the rewind must hit the same database the API is on.
      POSTGRES_URL: "postgresql://postgres:sauti-e2e@localhost:55432/postgres",
    },
  });
  return parseInt(out.trim(), 10);
}
