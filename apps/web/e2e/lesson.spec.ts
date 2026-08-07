import { expect, test } from "@playwright/test";
import { freshUser, getJson, type RoadmapPayload } from "./helpers";

/**
 * Journey 4 — Roadmap → open a lesson → grammar + umuco note → quick check
 * (feedback for wrong AND right answers) → "Practice these words".
 */
test("roadmap → lesson content → quick check feedback → practice words", async ({
  page,
}) => {
  test.setTimeout(180_000); // roadmap + lesson + reload + deck loads, remote DB
  const { token } = await freshUser(page, "j4-lesson");

  // The fresh user's current lesson is the first one; learn its quick-check
  // answer key from the roadmap payload (the UI never exposes correctness).
  const roadmap = await getJson<RoadmapPayload>(page.request, "/roadmap", token);
  const firstLesson = roadmap.levels[0].units[0].lessons[0];
  const quickCheck = firstLesson.quick_check!;
  const correct = quickCheck.options.find((o) => o.correct)!.text;
  const wrong = quickCheck.options.find((o) => !o.correct)!.text;

  await page.goto("/roadmap");
  await expect(page.getByTestId("placement-cta")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("roadmap-level-A1")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("roadmap-level-A1")).toContainText("You are here");

  // Open the current unit → first lesson.
  await page.getByTestId("roadmap-unit").first().click();
  await page.waitForURL("**/lesson/**");

  // Grammar content, examples with audio, and the Umuco culture note.
  await expect(page.getByTestId("lesson")).toContainText(firstLesson.title, {
    timeout: 30_000,
  });
  await expect(page.getByTestId("grammar-md")).toBeVisible();
  await expect(page.getByTestId("example-row").first()).toBeVisible();
  await expect(page.getByTestId("play-audio").first()).toBeVisible();
  await expect(page.getByTestId("umuco-note")).toBeVisible();
  await expect(page.getByTestId("umuco-note")).toContainText("Umuco");

  // Quick check — wrong option first: corrective feedback names the answer.
  const option = (text: string) =>
    page
      .getByTestId("quick-check-option")
      .filter({ has: page.getByText(text, { exact: true }) })
      .first();

  await expect(page.getByTestId("quick-check")).toBeVisible();
  await option(wrong).click();
  await expect(page.getByTestId("mcq-feedback")).toBeVisible();
  await expect(page.getByTestId("mcq-feedback")).toContainText("Not quite");
  await expect(page.getByTestId("mcq-feedback")).toContainText(correct);

  // Remount (reload) and answer correctly: affirmative feedback.
  await page.reload();
  await expect(page.getByTestId("quick-check")).toBeVisible({ timeout: 30_000 });
  await option(correct).click();
  await expect(page.getByTestId("mcq-feedback")).toBeVisible();
  await expect(page.getByTestId("mcq-feedback")).toContainText("Yego!");

  // "Practice these words" → the lesson's situation deck.
  await page.getByTestId("practice-words").click();
  await page.waitForURL("**/vocab/**");
  await expect(page.getByTestId("review-card")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("reveal-card")).toBeVisible();
});
