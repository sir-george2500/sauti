import { expect, test, type APIResponse } from "@playwright/test";
import { API_BASE, PASSWORD, uniqueEmail, allItems, type RoadmapPayload } from "./helpers";

/**
 * API-level e2e (Playwright request contexts against the real API):
 *  - refresh rotation happy path,
 *  - reuse of a rotated refresh cookie → 401 + family revocation,
 *  - speech scoring determinism (same input → same PronReport).
 */

function refreshCookie(res: APIResponse): string {
  const header = res
    .headersArray()
    .find(
      (h) =>
        h.name.toLowerCase() === "set-cookie" && h.value.startsWith("sauti_refresh="),
    );
  expect(header, "login/refresh must set the sauti_refresh cookie").toBeTruthy();
  return header!.value.split(";")[0]; // "sauti_refresh=<raw>"
}

test("refresh rotation: happy path, reuse → 401, family revoked", async ({
  playwright,
}) => {
  test.setTimeout(120_000); // pure API, but every call crosses to the remote DB
  const email = uniqueEmail("api-auth");

  // Register + login in a throwaway context; capture the raw cookie ourselves
  // so the automatic cookie jar can't mask reuse.
  const bootstrap = await playwright.request.newContext();
  const reg = await bootstrap.post(`${API_BASE}/auth/register`, {
    data: { email, password: PASSWORD, course_code: "KIN", pace_hours_week: 5 },
  });
  expect(reg.status()).toBe(201);
  const login = await bootstrap.post(`${API_BASE}/auth/login`, {
    data: { email, password: PASSWORD },
  });
  expect(login.status()).toBe(200);
  const cookie1 = refreshCookie(login);
  await bootstrap.dispose();

  // Happy path: cookie1 → new access token + rotated cookie2 ≠ cookie1.
  const ctx1 = await playwright.request.newContext();
  const refresh1 = await ctx1.post(`${API_BASE}/auth/refresh`, {
    headers: { Cookie: cookie1 },
  });
  expect(refresh1.status()).toBe(200);
  const body1 = (await refresh1.json()) as { access_token: string };
  expect(body1.access_token).toBeTruthy();
  const cookie2 = refreshCookie(refresh1);
  expect(cookie2).not.toBe(cookie1);

  // The rotated access token works.
  const me = await ctx1.get(`${API_BASE}/me`, {
    headers: { Authorization: `Bearer ${body1.access_token}` },
  });
  expect(me.status()).toBe(200);
  await ctx1.dispose();

  // Reuse of the ALREADY-ROTATED cookie1 → 401 (reuse detection)…
  const ctx2 = await playwright.request.newContext();
  const reuse = await ctx2.post(`${API_BASE}/auth/refresh`, {
    headers: { Cookie: cookie1 },
  });
  expect(reuse.status()).toBe(401);
  await ctx2.dispose();

  // …and the whole family is revoked: the still-fresh cookie2 dies too.
  const ctx3 = await playwright.request.newContext();
  const afterRevoke = await ctx3.post(`${API_BASE}/auth/refresh`, {
    headers: { Cookie: cookie2 },
  });
  expect(afterRevoke.status()).toBe(401);
  await ctx3.dispose();
});

test("speech scoring is deterministic: same input → same PronReport", async ({
  playwright,
}) => {
  test.setTimeout(120_000); // pure API, but every call crosses to the remote DB
  const ctx = await playwright.request.newContext();
  const email = uniqueEmail("api-speech");
  const reg = await ctx.post(`${API_BASE}/auth/register`, {
    data: { email, password: PASSWORD, course_code: "KIN", pace_hours_week: 5 },
  });
  expect(reg.status()).toBe(201);
  const login = await ctx.post(`${API_BASE}/auth/login`, {
    data: { email, password: PASSWORD },
  });
  const { access_token } = (await login.json()) as { access_token: string };
  const auth = { Authorization: `Bearer ${access_token}` };

  const roadmapRes = await ctx.get(`${API_BASE}/roadmap`, { headers: auth });
  expect(roadmapRes.status()).toBe(200);
  const item = allItems((await roadmapRes.json()) as RoadmapPayload)[0];

  // Server-issued upload ref (made-up refs are rejected), then PUT the take.
  const uploadUrlRes = await ctx.post(`${API_BASE}/speech/upload-url`, {
    headers: auth,
    data: { content_type: "audio/webm" },
  });
  expect(uploadUrlRes.status()).toBe(200);
  const { upload_url, audio_ref } = (await uploadUrlRes.json()) as {
    upload_url: string;
    audio_ref: string;
  };
  const put = await ctx.put(upload_url, {
    headers: { "Content-Type": "audio/webm" },
    data: Buffer.from("e2e-fake-audio-take"),
  });
  expect(put.status()).toBe(204);

  // Same (item_id, audio_ref) → byte-identical PronReport, twice.
  const score = () =>
    ctx.post(`${API_BASE}/speech/score`, {
      headers: auth,
      data: { item_id: item.id, audio_ref },
    });
  const first = await score();
  expect(first.status()).toBe(200);
  const report1 = await first.json();
  const second = await score();
  expect(second.status()).toBe(200);
  const report2 = await second.json();
  expect(report2).toEqual(report1);

  // Shape sanity per SPEC §3 PronReport.
  expect(report1.overall).toBeGreaterThanOrEqual(60);
  expect(report1.overall).toBeLessThanOrEqual(95);
  expect(Array.isArray(report1.phonemes)).toBe(true);
  expect(report1.phonemes.length).toBeGreaterThan(0);
  expect(Array.isArray(report1.tone_flags)).toBe(true);

  // A speak attempt with the same audio_ref returns the same pron report.
  const attempt = await ctx.post(`${API_BASE}/attempts`, {
    headers: auth,
    data: {
      item_id: item.id,
      mode: "speak",
      score: report1.overall / 100,
      audio_ref,
    },
  });
  expect(attempt.status()).toBe(200);
  const attemptBody = await attempt.json();
  expect(attemptBody.pron).toEqual(report1);

  await ctx.dispose();
});
