import { beforeEach, describe, expect, it, vi } from "vitest";

/**
 * Tests the fetch wrapper's refresh-retry behaviour (SPEC §5 errors: on 401
 * the client refreshes once and retries once). Module state (token +
 * single-flight promise) is reset via vi.resetModules().
 */

type ClientModule = typeof import("./client");

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

async function loadClient(): Promise<ClientModule> {
  vi.resetModules();
  return import("./client");
}

describe("apiFetch", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("attaches the bearer token and parses JSON", async () => {
    const client = await loadClient();
    client.setAccessToken("tok-1");
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await client.apiFetch<{ ok: boolean }>("/me");

    expect(result).toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${client.API_BASE_URL}/me`);
    expect(init.headers.Authorization).toBe("Bearer tok-1");
    expect(init.credentials).toBe("include");
  });

  it("on 401 refreshes once, then retries with the new token", async () => {
    const client = await loadClient();
    client.setAccessToken("stale");
    const fetchMock = vi
      .fn()
      // original request → 401
      .mockResolvedValueOnce(jsonResponse(401, { code: "token_expired", message: "expired" }))
      // refresh → new token
      .mockResolvedValueOnce(jsonResponse(200, { access_token: "fresh", user: { id: "u1" } }))
      // retried request → success
      .mockResolvedValueOnce(jsonResponse(200, { hello: "again" }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await client.apiFetch<{ hello: string }>("/me");

    expect(result).toEqual({ hello: "again" });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[1][0]).toBe(`${client.API_BASE_URL}/auth/refresh`);
    expect(fetchMock.mock.calls[1][1].credentials).toBe("include");
    expect(fetchMock.mock.calls[2][1].headers.Authorization).toBe("Bearer fresh");
    expect(client.getAccessToken()).toBe("fresh");
  });

  it("throws ApiError(401) and clears the token when refresh fails", async () => {
    const client = await loadClient();
    client.setAccessToken("stale");
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(401, { code: "token_expired", message: "expired" }))
      .mockResolvedValueOnce(jsonResponse(401, { code: "refresh_revoked", message: "gone" }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(client.apiFetch("/me")).rejects.toMatchObject({
      name: "ApiError",
      status: 401,
    });
    // Original + refresh only — no retry loop.
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(client.getAccessToken()).toBeNull();
  });

  it("retries at most once even if the retried request 401s again", async () => {
    const client = await loadClient();
    client.setAccessToken("stale");
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(401, { code: "token_expired", message: "expired" }))
      .mockResolvedValueOnce(jsonResponse(200, { access_token: "fresh", user: { id: "u1" } }))
      .mockResolvedValueOnce(jsonResponse(401, { code: "nope", message: "still no" }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(client.apiFetch("/me")).rejects.toMatchObject({ status: 401, code: "nope" });
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("shares a single refresh across concurrent 401s", async () => {
    const client = await loadClient();
    client.setAccessToken("stale");
    let refreshCalls = 0;
    const fetchMock = vi.fn().mockImplementation((url: string, init: RequestInit) => {
      if (url.endsWith("/auth/refresh")) {
        refreshCalls += 1;
        return Promise.resolve(
          jsonResponse(200, { access_token: "fresh", user: { id: "u1" } }),
        );
      }
      const headers = init.headers as Record<string, string>;
      if (headers.Authorization === "Bearer fresh") {
        return Promise.resolve(jsonResponse(200, { ok: true }));
      }
      return Promise.resolve(jsonResponse(401, { code: "token_expired", message: "expired" }));
    });
    vi.stubGlobal("fetch", fetchMock);

    const [a, b] = await Promise.all([
      client.apiFetch<{ ok: boolean }>("/session/today"),
      client.apiFetch<{ ok: boolean }>("/progress"),
    ]);

    expect(a).toEqual({ ok: true });
    expect(b).toEqual({ ok: true });
    expect(refreshCalls).toBe(1);
  });

  it("throws ApiError with the RFC7807-ish body on non-401 failures", async () => {
    const client = await loadClient();
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse(422, { code: "validation_error", message: "Bad payload" }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(client.apiFetch("/attempts", { method: "POST", body: {} })).rejects.toMatchObject({
      status: 422,
      code: "validation_error",
      message: "Bad payload",
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
