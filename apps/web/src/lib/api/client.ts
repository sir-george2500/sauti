import type { ApiErrorBody, AuthResponse } from "./types";

/**
 * API client (SPEC §5). Access token lives in module memory only — never in
 * localStorage. The refresh token is an httpOnly cookie the browser sends to
 * POST /auth/refresh with credentials:'include'. On a 401 the wrapper
 * refreshes once (single-flight across concurrent requests) and retries the
 * original request exactly once.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly detail?: unknown;

  constructor(status: number, body: Partial<ApiErrorBody> | null) {
    super(body?.message ?? `Request failed (${status})`);
    this.name = "ApiError";
    this.status = status;
    this.code = body?.code ?? "unknown";
    this.detail = body?.detail;
  }
}

async function parseErrorBody(res: Response): Promise<Partial<ApiErrorBody> | null> {
  try {
    return (await res.json()) as Partial<ApiErrorBody>;
  } catch {
    return null;
  }
}

// Single-flight refresh: concurrent 401s share one refresh round-trip.
let refreshPromise: Promise<boolean> | null = null;

/**
 * Rotate the refresh cookie and store the new access token.
 * Resolves true on success, false if the session is gone.
 */
export function refreshAccessToken(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: "POST",
          credentials: "include",
        });
        if (!res.ok) {
          setAccessToken(null);
          return false;
        }
        const body = (await res.json()) as AuthResponse;
        setAccessToken(body.access_token);
        return true;
      } catch {
        setAccessToken(null);
        return false;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

export interface ApiFetchOptions {
  method?: string;
  body?: unknown;
  signal?: AbortSignal;
  /** Internal: prevents a second refresh-retry loop. */
  _retried?: boolean;
}

/**
 * Fetch `path` (relative to API_BASE_URL) as JSON.
 * - Attaches `Authorization: Bearer <token>` when a token is held.
 * - On 401: refreshes once, then retries the request once.
 * - Non-2xx: throws ApiError with the RFC7807-ish body when present.
 */
export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const { method = "GET", body, signal, _retried = false } = options;

  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;

  const res = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    credentials: "include",
    signal,
  });

  if (res.status === 401 && !_retried) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return apiFetch<T>(path, { method, body, signal, _retried: true });
    }
    throw new ApiError(401, await parseErrorBody(res));
  }

  if (!res.ok) {
    throw new ApiError(res.status, await parseErrorBody(res));
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/** URL an <audio> element can play for a curriculum item (302 to audio). */
export function ttsUrl(itemId: string): string {
  return `${API_BASE_URL}/tts/${itemId}`;
}

/** WebSocket URL for the conversation loop, token passed as query param. */
export function conversationWsUrl(scenarioId: string): string {
  const base = API_BASE_URL.replace(/^http/, "ws");
  const token = accessToken ? `?token=${encodeURIComponent(accessToken)}` : "";
  return `${base}/ws/conversation/${scenarioId}${token}`;
}
