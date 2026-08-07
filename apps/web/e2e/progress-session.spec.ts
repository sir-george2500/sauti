import { expect, test } from "@playwright/test";
import {
  allItems,
  freshUser,
  getJson,
  postJson,
  type RoadmapPayload,
} from "./helpers";

/**
 * Journeys 8 & 9 — Progress after real activity, and Start session from Today.
 */

test("progress shows totals, skill bars and can-do counts after activity", async ({
  page,
}) => {
  test.setTimeout(180_000); // seeds 9 attempts + heaviest endpoint fan-out
  const { token } = await freshUser(page, "j8-progress");

  // Real activity via the API: 8 good read reviews + 1 strong speaking attempt
  // (score ≥ 0.8 confirms the level's next speak can-do server-side).
  const roadmap = await getJson<RoadmapPayload>(page.request, "/roadmap", token);
  const items = allItems(roadmap).slice(0, 8);
  await Promise.all(
    items.map((i) =>
      postJson(page.request, "/attempts", token, {
        item_id: i.id,
        mode: "read",
        score: 1,
      }),
    ),
  );
  const speak = await postJson<{ confirmed_candos?: string[] }>(
    page.request,
    "/attempts",
    token,
    { item_id: items[0].id, mode: "speak", score: 0.9 },
  );
  expect(speak.confirmed_candos?.length).toBe(1);

  await page.goto("/progress");

  // The progress endpoint is the heaviest query fan-out — wait for the page
  // to finish its first render before asserting details.
  await expect(page.getByTestId("skill-balance")).toBeVisible({ timeout: 60_000 });

  // Totals moved: 9 attempts ≈ 0.1 h, 1 sentence spoken.
  await expect(page.getByTestId("total-time")).toContainText("0.1 h");
  await expect(page.getByTestId("sentences-spoken")).toContainText("1");

  // Skill balance bars for all four skills, each labelled with a CEFR.
  for (const skill of ["speaking", "listening", "reading", "writing"]) {
    await expect(page.getByTestId(`skill-${skill}`)).toBeVisible();
    await expect(page.getByTestId(`skill-${skill}`)).toContainText(/A1|A2|B1/);
  }

  // Can-do checklist: exactly one confirmed in a live speaking check.
  await expect(page.getByTestId("cando-count")).toContainText(/^1 of \d+ confirmed/);
  await expect(page.getByTestId("cando-item").first()).toBeVisible();
  await expect(
    page.getByTestId("cando-item").filter({ hasText: "✓" }).first(),
  ).toBeVisible();

  // Today's activity counts toward consistency.
  await expect(page.getByTestId("consistency-progress")).toContainText(
    "1 of the last 14 days",
  );
});

test("Start session from Today opens the plan's first block", async ({ page }) => {
  test.setTimeout(120_000);
  await freshUser(page, "j9-session");

  await page.goto("/");
  await expect(page.getByTestId("session-card")).toBeVisible({ timeout: 30_000 });

  // A fresh user has nothing due → the plan is lesson + speak (2 blocks).
  await expect(page.getByTestId("session-block")).toHaveCount(2, {
    timeout: 30_000,
  });
  await expect(page.getByTestId("session-card")).toContainText("25 minutes");

  await page.getByTestId("start-session").click();

  // First block is the current lesson: the lesson player opens with content.
  await page.waitForURL("**/lesson/**");
  await expect(page.getByTestId("grammar-md")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("quick-check")).toBeVisible();
});
