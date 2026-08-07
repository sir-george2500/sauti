import { expect, test, type Page } from "@playwright/test";
import {
  freshUser,
  getJson,
  lessonQuizOf,
  postJson,
  type RoadmapPayload,
} from "./helpers";

/**
 * Journey 4 — Roadmap → open a lesson → grammar + umuco note → the
 * multi-question lesson quiz (wrong AND right paths, explanations, summary,
 * retake) → "Practice these words".
 */

/** An option button of the on-screen quiz question by its exact text. */
const option = (page: Page, text: string) =>
  page
    .getByTestId("quick-check-option")
    .filter({ has: page.getByText(text, { exact: true }) })
    .first();

test("roadmap → lesson content → quiz with feedback + summary → practice words", async ({
  page,
}) => {
  test.setTimeout(240_000); // roadmap + a full quiz of attempts + deck load
  const { token } = await freshUser(page, "j4-lesson");

  // Learn the quiz answer key from the roadmap payload (the UI never exposes
  // correctness). Falls back to the single quick_check pre-rollout.
  const roadmap = await getJson<RoadmapPayload>(page.request, "/roadmap", token);
  const firstLesson = roadmap.levels[0].units[0].lessons[0];
  const quiz = lessonQuizOf(firstLesson);
  expect(quiz.length).toBeGreaterThan(0);

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

  // Quiz: wrong on the first question, right on the rest. Every answer posts
  // one read-mode attempt; every answer shows feedback + explanation.
  await expect(page.getByTestId("quick-check")).toBeVisible();
  for (let i = 0; i < quiz.length; i++) {
    await expect(page.getByTestId("quiz-progress")).toContainText(
      `Question ${i + 1} of ${quiz.length}`,
    );
    const q = quiz[i];
    const correct = q.options.find((o) => o.correct)!.text;
    const wrong = q.options.find((o) => !o.correct)!.text;
    const pick = i === 0 ? wrong : correct;

    const [attemptRes] = await Promise.all([
      page.waitForResponse(
        (r) => r.url().includes("/attempts") && r.request().method() === "POST",
      ),
      option(page, pick).click(),
    ]);
    expect(attemptRes.status()).toBe(200);
    const attemptBody = (await attemptRes.request().postDataJSON()) as {
      mode: string;
      score: number;
      item_id: string;
    };
    expect(attemptBody.mode).toBe("read");
    expect(attemptBody.score).toBe(i === 0 ? 0 : 1);
    expect(attemptBody.item_id).toBeTruthy();

    await expect(page.getByTestId("quiz-explanation")).toBeVisible();
    if (i === 0) {
      // Corrective feedback names the right answer.
      await expect(page.getByTestId("quiz-explanation")).toContainText("Not quite");
      await expect(page.getByTestId("quiz-explanation")).toContainText(correct);
    } else {
      await expect(page.getByTestId("quiz-explanation")).toContainText("Yego");
    }
    await page.getByTestId("quiz-next").click();
  }

  // Summary: score, per-kind breakdown chips, retake resets to question 1.
  await expect(page.getByTestId("quiz-summary")).toBeVisible();
  await expect(page.getByTestId("quiz-summary")).toContainText(
    `You got ${quiz.length - 1} of ${quiz.length}`,
  );
  expect(await page.getByTestId("quiz-kind-score").count()).toBeGreaterThan(0);
  await page.getByTestId("quiz-retake").click();
  await expect(page.getByTestId("quiz-progress")).toContainText(
    `Question 1 of ${quiz.length}`,
  );

  // "Practice these words" → the lesson's situation deck.
  await page.getByTestId("practice-words").click();
  await page.waitForURL("**/vocab/**");
  await expect(page.getByTestId("review-card")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("reveal-card")).toBeVisible();
});

/**
 * Journey 4b — revision navigation. Open lesson 1.2 → "← Lesson 1.1" lands on
 * the previous lesson's content (and forward again); finish 1.1, then reopen
 * it from the roadmap's done-lesson pill.
 */
test("lesson prev/next navigation + reopening a done lesson from the roadmap", async ({
  page,
}) => {
  test.setTimeout(240_000);
  const { token } = await freshUser(page, "j4b-nav");

  const roadmap = await getJson<RoadmapPayload>(page.request, "/roadmap", token);
  const unit1 = roadmap.levels[0].units[0];
  const [l1, l2] = unit1.lessons;
  expect(l2, "seed must give unit 1 at least two lessons").toBeTruthy();

  // Open lesson 1.2 directly (status "available" for a fresh user).
  await page.goto(`/lesson/${l2.id}`);
  await expect(page.getByTestId("lesson")).toContainText(l2.title, { timeout: 30_000 });
  await expect(page.getByTestId("lesson-prev")).toContainText("Lesson 1.1");

  // ← back to 1.1 for revision.
  await page.getByTestId("lesson-prev").click();
  await page.waitForURL(`**/lesson/${l1.id}`);
  await expect(page.getByTestId("lesson")).toContainText(l1.title);
  await expect(page.getByTestId("grammar-md")).toBeVisible();

  // → forward to 1.2 again (available, so the link is live).
  await expect(page.getByTestId("lesson-next")).toContainText("Lesson 1.2");
  await page.getByTestId("lesson-next").click();
  await page.waitForURL(`**/lesson/${l2.id}`);
  await expect(page.getByTestId("lesson")).toContainText(l2.title);

  // Complete lesson 1.1 (attempt every item), then reopen it from the roadmap:
  // the done pill must stay clickable for revision.
  for (const item of l1.items ?? []) {
    await postJson(page.request, "/attempts", token, {
      item_id: item.id,
      mode: "read",
      score: 1,
    });
  }
  await page.goto("/roadmap");
  const donePill = page
    .locator('[data-testid="roadmap-lesson"][data-status="done"]')
    .first();
  await expect(donePill).toBeVisible({ timeout: 30_000 });
  await expect(donePill).toContainText("1.1");
  // The road has moved on — 1.2 is now the current lesson…
  await expect(
    page.locator('[data-testid="roadmap-lesson"][data-status="current"]').first(),
  ).toContainText("1.2");
  // …but the finished lesson reopens.
  await donePill.click();
  await page.waitForURL(`**/lesson/${l1.id}`);
  await expect(page.getByTestId("lesson")).toContainText(l1.title, { timeout: 30_000 });
});
