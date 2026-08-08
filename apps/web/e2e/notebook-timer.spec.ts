import { expect, test } from "@playwright/test";
import { freshUser, getJson, type RoadmapPayload } from "./helpers";

/**
 * Journey 10 — Ikaye (the word notebook) and the daily study timer.
 *
 * The notebook is the learner's own record: a bookmark on any sentence keeps
 * it, and a personal note explains why it mattered. The timer is the "learn
 * for 15 minutes a day" commitment — a goal on the profile plus a countdown
 * that survives a reload.
 */

interface NotebookEntryPayload {
  id: string;
  item_id?: string | null;
  text: string;
  note?: string | null;
}

test("save a word from a lesson → it lands in the notebook with a note", async ({ page }) => {
  test.setTimeout(180_000);
  const { token } = await freshUser(page, "j10-notebook");

  const roadmap = await getJson<RoadmapPayload>(page.request, "/roadmap", token);
  const lesson = roadmap.levels[0].units[0].lessons[0];
  const item = (lesson.items ?? [])[0];
  expect(item, "seeded lesson has items").toBeTruthy();

  // Bookmark the first example row.
  await page.goto(`/lesson/${lesson.id}`);
  const bookmark = page.getByTestId("save-to-notebook").first();
  await expect(bookmark).toBeVisible({ timeout: 40_000 });
  await expect(bookmark).toHaveAttribute("data-saved", "false");
  await bookmark.click();
  await expect(bookmark).toHaveAttribute("data-saved", "true", { timeout: 20_000 });

  // The API kept it, snapshotting the item's sentence.
  const entries = await getJson<NotebookEntryPayload[]>(page.request, "/notebook", token);
  expect(entries).toHaveLength(1);
  expect(entries[0].item_id).toBe(item.id);
  expect(entries[0].text).toBe(item.sentence);

  // It shows on the notebook page, and a note can be attached.
  await page.goto("/notebook");
  const entry = page.getByTestId("notebook-entry").first();
  await expect(entry).toBeVisible({ timeout: 40_000 });
  await expect(entry).toContainText(item.sentence);
  await expect(entry.getByTestId("notebook-play")).toBeVisible();

  await entry.getByTestId("notebook-edit-note").click();
  await entry.getByTestId("notebook-note-input").fill("Heard this at the market gate.");
  await entry.getByTestId("notebook-save").click();
  await expect(entry).toContainText("Heard this at the market gate.", { timeout: 20_000 });

  // The note persists server-side, not just in the page.
  await expect(async () => {
    const fresh = await getJson<NotebookEntryPayload[]>(page.request, "/notebook", token);
    expect(fresh[0].note).toBe("Heard this at the market gate.");
  }).toPass({ timeout: 20_000 });
});

test("add a free-form word, then remove it", async ({ page }) => {
  test.setTimeout(150_000);
  await freshUser(page, "j10-freeform");

  await page.goto("/notebook");
  await expect(page.getByTestId("notebook-empty")).toBeVisible({ timeout: 40_000 });

  await page.getByTestId("notebook-add-text").fill("Ikaramu");
  await page.getByTestId("notebook-add-gloss").fill("pen");
  await page.getByTestId("notebook-add-note").fill("From the shop next door.");
  await page.getByTestId("notebook-add").click();

  const entry = page.getByTestId("notebook-entry").first();
  await expect(entry).toContainText("Ikaramu", { timeout: 20_000 });
  await expect(entry).toContainText("pen");
  await expect(entry).toContainText("From the shop next door.");

  // Delete asks once, then removes.
  await entry.getByTestId("notebook-delete").click();
  await expect(entry.getByTestId("notebook-delete")).toContainText("Really remove?");
  await entry.getByTestId("notebook-delete").click();
  await expect(page.getByTestId("notebook-empty")).toBeVisible({ timeout: 20_000 });
});

test("daily timer: set a 15-minute goal, run it, and keep progress across a reload", async ({
  page,
}) => {
  test.setTimeout(180_000);
  await freshUser(page, "j10-timer");

  await page.goto("/");
  const timer = page.getByTestId("daily-timer");
  await expect(timer).toBeVisible({ timeout: 60_000 });

  // Choose the 15-minute goal (persisted on the profile).
  await timer.getByTestId("change-goal").click();
  await timer.getByTestId("goal-option-15").click();
  await expect(timer.getByTestId("change-goal")).toContainText("15 min", { timeout: 20_000 });
  await expect(timer.getByTestId("timer-remaining")).toHaveText("15:00");

  // Start it and let it tick.
  await timer.getByTestId("timer-toggle").click();
  await expect(timer.getByTestId("timer-toggle")).toHaveText("Pause");
  await expect
    .poll(async () => timer.getByTestId("timer-remaining").textContent(), { timeout: 20_000 })
    .not.toBe("15:00");

  const banked = await timer.getByTestId("timer-remaining").textContent();
  await timer.getByTestId("timer-toggle").click(); // pause
  await expect(timer.getByTestId("timer-status")).toContainText("Paused");

  // A reload keeps the minutes already put in, and the goal came from the API.
  await page.reload();
  await expect(timer.getByTestId("change-goal")).toContainText("15 min", { timeout: 60_000 });
  await expect(timer.getByTestId("timer-remaining")).not.toHaveText("15:00");
  const afterReload = await timer.getByTestId("timer-remaining").textContent();
  expect(Number(afterReload!.split(":")[1])).toBeLessThanOrEqual(
    Number(banked!.split(":")[1]),
  );
  await expect(timer.getByTestId("timer-toggle")).toHaveText("Resume");
});
