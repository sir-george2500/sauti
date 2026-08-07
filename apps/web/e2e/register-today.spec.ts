import { expect, test } from "@playwright/test";
import { uniqueEmail, PASSWORD } from "./helpers";

/**
 * Journey 1 — Register (Ikinyarwanda + pace) → placement intro →
 * "I'm brand new — start at A1" → Today dashboard.
 */
test("register → start at A1 → Today dashboard", async ({ page }) => {
  test.setTimeout(120_000); // several remote-DB page loads
  const email = uniqueEmail("j1-register");

  await page.goto("/register");
  await expect(page.getByTestId("register-form")).toBeVisible();

  // Pick Ikinyarwanda and a weekly pace explicitly.
  await page.getByTestId("course-KIN").click();
  await page.getByTestId("pace-5").click();
  await page.getByTestId("register-email").fill(email);
  await page.getByTestId("register-password").fill(PASSWORD);
  await page.getByTestId("register-submit").click();

  // Register auto-logs-in and lands on the placement intro.
  await page.waitForURL("**/placement");
  await expect(page.getByTestId("begin-placement")).toBeVisible();

  // Escape hatch: brand new — start at A1.
  await page.getByTestId("start-at-a1").click();
  await page.waitForURL(/\/$/);

  // Today dashboard: greeting, session card, where-you-are, consistency, proverb.
  // First-render waits are generous: each card is fed by its own slow query.
  await expect(page.getByTestId("greeting")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("greeting")).toContainText(/Mwaramutse|Mwiriwe|Muraho/);

  await expect(page.getByTestId("session-card")).toBeVisible();
  await expect(page.getByTestId("session-block").first()).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.getByTestId("start-session")).toBeVisible();

  // Fresh unplaced profile behaves as A1 — the where-you-are card says so.
  await expect(page.getByTestId("where-you-are")).toBeVisible();
  await expect(page.getByTestId("where-you-are")).toContainText("A1", {
    timeout: 30_000,
  });
  await expect(page.getByTestId("where-you-are")).toContainText("Greetings & people");

  // Consistency card (rhythm beats streaks) — day zero shows 0 of 14.
  await expect(page.getByTestId("consistency")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("consistency")).toContainText("of the last 14 days");

  // Proverb of the day.
  await expect(page.getByTestId("proverb-card")).toBeVisible();
  await expect(page.getByTestId("proverb-card")).toContainText("proverb of the day");
});
