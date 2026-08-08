import { expect, test } from "@playwright/test";
import { freshUser, getJson, type RoadmapPayload } from "./helpers";

/**
 * Journey — Mwarimu, the floating study buddy.
 *
 * The FAB rides in the app shell, so it is present on every authenticated page
 * and absent from /login. With SAUTI_FAKE_AI=1 the buddy socket answers
 * deterministically and hands back one navigate action, which the panel
 * renders as a chip that routes in-app.
 */

test("study buddy: everywhere but /login, chats, guides, and remembers", async ({ page }) => {
  test.setTimeout(180_000);
  const { token } = await freshUser(page, "j-buddy");

  const roadmap = await getJson<RoadmapPayload>(page.request, "/roadmap", token);
  const lessonId = roadmap.levels[0].units[0].lessons[0].id;

  // --- The FAB is on Today, and survives a route change --------------------
  await page.goto("/");
  const fab = page.getByTestId("buddy-fab");
  await expect(fab).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("buddy-panel")).toHaveCount(0);

  await page.goto(`/lesson/${lessonId}`);
  await expect(fab).toBeVisible({ timeout: 30_000 });

  // --- Open: greeting + opener chips, never a blank box --------------------
  await fab.click();
  const panel = page.getByTestId("buddy-panel");
  const messages = page.getByTestId("buddy-message");
  await expect(panel).toBeVisible();
  await expect(panel).toContainText("Mwarimu");
  await expect(messages).toHaveCount(1); // the static, free hello
  await expect(messages.first()).toContainText("Mwarimu here");

  // An opener chip fills the input rather than sending blind.
  const input = page.getByTestId("buddy-input");
  await page.getByTestId("buddy-opener").first().click();
  await expect(input).not.toHaveValue("");

  // --- Send a turn → reply → guidance chip ---------------------------------
  await input.fill("What should I do next?");
  await page.getByTestId("buddy-send").click();
  await expect(messages.nth(1)).toContainText("What should I do next?");
  // Learner turn + at least one buddy turn on top of the greeting.
  await expect(messages.nth(2)).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("buddy-typing")).toHaveCount(0, { timeout: 30_000 });
  const said = await messages.count();
  expect(said).toBeGreaterThanOrEqual(3);

  const chip = page.getByTestId("buddy-action").first();
  await expect(chip).toBeVisible({ timeout: 30_000 });
  const target = await chip.getAttribute("data-href");
  expect(target, "action chips only carry in-app paths").toMatch(/^\/[^/]*/);

  // --- Escape closes; the conversation survives a reopen -------------------
  await page.keyboard.press("Escape");
  await expect(panel).toHaveCount(0);
  await fab.click();
  await expect(messages).toHaveCount(said);

  // --- The chip navigates in-app and closes the panel ----------------------
  await page.getByTestId("buddy-action").first().click();
  await expect(page.getByTestId("buddy-panel")).toHaveCount(0);
  await page.waitForURL((url) => url.pathname + url.search === target, { timeout: 30_000 });

  // A real in-app route: the shell (and its FAB) came along, and the chat is
  // still there after the navigation the buddy suggested.
  await expect(page.getByTestId("buddy-fab")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("buddy-fab").click();
  await expect(page.getByTestId("buddy-message")).toHaveCount(said);
});

test("study buddy stays off the unauthenticated pages", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByTestId("login-form")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("buddy-fab")).toHaveCount(0);
  await expect(page.getByTestId("buddy-panel")).toHaveCount(0);

  await page.goto("/register");
  await expect(page.getByTestId("register-form")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("buddy-fab")).toHaveCount(0);
});
