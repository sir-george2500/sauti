import { expect, test } from "@playwright/test";
import {
  allItems,
  freshUser,
  getJson,
  type RoadmapPayload,
} from "./helpers";

/**
 * Journey 3 — full adaptive placement: answer MCQs until the result appears.
 *
 * Answers are chosen CORRECTLY on purpose: the prompt is always
 * “What does “<sentence>” mean?” and the right option is that item's gloss,
 * which we learn from GET /roadmap (it embeds every course item). All-correct
 * answers drive theta up deterministically, the engine stops at 12 questions
 * and clamps the result to the highest seeded KIN level → A2.
 */
test("adaptive placement MCQ flow places the user at A2", async ({ page }) => {
  // 12 adaptive answers, each a multi-query round trip to the remote DB
  // (~8-10 s apiece observed) — this is legitimately the longest journey.
  test.setTimeout(300_000);
  const { token } = await freshUser(page, "j3-placement");

  const roadmap = await getJson<RoadmapPayload>(page.request, "/roadmap", token);
  const glossBySentence = new Map(allItems(roadmap).map((i) => [i.sentence, i.gloss]));

  await page.goto("/placement");
  await expect(page.getByTestId("begin-placement")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("begin-placement").click();
  await expect(page.getByTestId("placement-question")).toBeVisible({
    timeout: 30_000,
  });

  const MAX_QUESTIONS = 20; // engine caps at 18; sane loop guard
  for (let n = 0; n < MAX_QUESTIONS; n++) {
    if (await page.getByTestId("placement-result").isVisible()) break;

    const card = page.getByTestId("placement-question");
    await expect(card).toBeVisible();
    const prompt = await card.locator("p.ky").first().innerText();
    const sentence = prompt.match(/“(.+)”/)?.[1];
    const gloss = sentence ? glossBySentence.get(sentence) : undefined;

    const options = page.getByTestId("placement-answer");
    if (gloss) {
      await options
        .filter({ has: page.getByText(gloss, { exact: true }) })
        .first()
        .click();
    } else {
      await options.first().click(); // fallback: still progresses the flow
    }
    await page.getByTestId("placement-submit").click();
    // Deterministic wait: either the result appears, or the server serves the
    // next question (its 1-based number always increments).
    await expect(
      page
        .getByTestId("placement-result")
        .or(page.getByText(`Question ${n + 2} of`)),
    ).toBeVisible({ timeout: 30_000 });
  }

  // Result: placed level is shown (all-correct → A2, the top seeded KIN level).
  await expect(page.getByTestId("placement-result")).toBeVisible();
  await expect(page.getByTestId("placement-result")).toContainText("A2");

  // Profile reflects the placement server-side.
  const me = await getJson<{ profile: { placed_level: string | null } }>(
    page.request,
    "/me",
    token,
  );
  expect(me.profile.placed_level).toBe("A2");

  // Finish returns to Today, which now shows the placed level's position.
  await page.getByTestId("placement-finish").click();
  await page.waitForURL(/\/$/);
  await expect(page.getByTestId("greeting")).toBeVisible({ timeout: 30_000 });
});
