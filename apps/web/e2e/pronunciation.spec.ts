import { expect, test } from "@playwright/test";
import { allItems, freshUser, getJson, type RoadmapPayload } from "./helpers";

/**
 * Journey 7 — Pronunciation practice, driven END-TO-END in the browser:
 * chromium runs with --use-fake-device-for-media-stream (see playwright
 * config), so MediaRecorder records a real (fake-device) take headless. The
 * page then uploads via POST /speech/upload-url + PUT, scores via
 * POST /speech/score (deterministic stub) and renders the PronReport.
 * API-level determinism of the score is additionally covered in api.spec.ts.
 */
test("pronunciation: native audio, record a take, score renders", async ({
  page,
}) => {
  test.setTimeout(180_000); // roadmap-backed item lookup + upload + score
  const { token } = await freshUser(page, "j7-pron");

  const roadmap = await getJson<RoadmapPayload>(page.request, "/roadmap", token);
  const item = allItems(roadmap)[0]; // "Mwaramutse!"

  await page.goto(`/practice/pronunciation/${item.id}`);

  // Target phrase + native audio controls.
  await expect(page.getByTestId("target-phrase")).toBeVisible({ timeout: 40_000 });
  await expect(page.getByTestId("target-phrase")).toContainText(item.sentence);
  await expect(page.getByTestId("play-native")).toBeVisible();
  await expect(page.getByTestId("play-slow")).toBeVisible();

  // Native audio plays (stub WAV) — give playback a brief moment, then pause.
  await page.getByTestId("play-native").click();
  await page.waitForTimeout(400); // audio playback needs a beat
  await page.getByTestId("play-native").click();

  // Record take 1 through the real UI flow.
  const record = page.getByTestId("record-button");
  await expect(record).toContainText("Record take 1");
  await record.click();
  await expect(record).toHaveAttribute("aria-pressed", "true");
  await page.waitForTimeout(900); // capture a short take from the fake mic
  await record.click(); // stop → upload → score → attempt

  // Score UI renders from the PronReport.
  await expect(page.getByTestId("pron-score")).toBeVisible({ timeout: 30_000 });
  const scoreText = await page
    .getByTestId("pron-score")
    .locator("p")
    .first()
    .innerText();
  const overall = parseInt(scoreText, 10);
  expect(overall).toBeGreaterThanOrEqual(60); // stub range is 60..95
  expect(overall).toBeLessThanOrEqual(95);

  // Per-syllable feedback chips.
  await expect(page.getByTestId("phoneme-chip").first()).toBeVisible();
  await expect(page.getByTestId("pron-score")).toContainText("Take 1");
  await expect(record).toContainText("Record take 2");
});
