import { expect, test } from "@playwright/test";
import {
  fakeRespelling,
  freshUser,
  getJson,
  playedRates,
  postJson,
  recordPlaybackRates,
  rewindSrsDue,
  stubPronunciation,
} from "./helpers";

interface DeckItems {
  tag: string;
  title: string;
  items: { id: string; sentence: string; gloss: string }[];
}

/**
 * Journey 5 — Vocab decks with due counts → SRS review flow → due count drops.
 *
 * Due state can't arise through the API alone (FSRS never schedules into the
 * past), so the test first creates SRS rows via real attempts (grade "again" →
 * due in 10 min) and then rewinds due_at by an hour directly in the DB
 * (helpers/rewind_srs_due.py — a stand-in for a time machine).
 */
test("decks show due counts; reviewing clears them", async ({ page }) => {
  test.setTimeout(300_000); // 28-card deck against a ~300 ms-RTT remote DB
  const { email, token } = await freshUser(page, "j5-vocab");

  // Seed SRS state on 6 greetings items via real attempts.
  const deck = await getJson<DeckItems>(page.request, "/vocab/decks/greetings", token);
  const seeded = deck.items.slice(0, 6);
  await Promise.all(
    seeded.map((i) =>
      postJson(page.request, "/attempts", token, {
        item_id: i.id,
        mode: "read",
        score: 0, // grade 1 (again)
      }),
    ),
  );
  expect(rewindSrsDue(email)).toBe(6);

  // Decks list shows the due counts.
  await page.goto("/vocab");
  await expect(page.getByTestId("review-due")).toBeVisible({ timeout: 40_000 });
  await expect(page.getByTestId("review-due")).toContainText("Review 6 due");
  const greetingsDeck = page
    .getByTestId("vocab-deck")
    .filter({ hasText: "Indamukanyo" });
  await expect(greetingsDeck.getByTestId("deck-due")).toHaveText("6 due for review");

  // Open the deck and review: reveal → grade good → next … until done.
  await greetingsDeck.click();
  await page.waitForURL("**/vocab/greetings");
  await expect(page.getByTestId("review-card")).toBeVisible({ timeout: 30_000 });

  // First card: reveal shows the gloss before grading.
  await page.getByTestId("reveal-card").click();
  await expect(page.getByTestId("review-gloss")).toBeVisible();
  await page.getByTestId("grade-good").click();

  const CARD_CAP = 40; // deck has 28 items; sane guard
  const reveal = page.getByTestId("reveal-card");
  const done = page.getByTestId("review-done");
  for (let i = 0; i < CARD_CAP; i++) {
    await expect(reveal.or(done)).toBeVisible();
    if (await done.isVisible()) break;
    await reveal.click();
    await page.getByTestId("grade-good").click();
  }
  await expect(done).toBeVisible();
  await expect(page.getByTestId("review-done")).toContainText("Byiza cyane!");

  // Back to decks: everything graded "good" is rescheduled → due count drops
  // to zero. Attempts post fire-and-forget, so poll until the last one lands.
  await page.getByTestId("back-to-decks").click();
  await page.waitForURL(/\/vocab$/);
  await expect(async () => {
    await page.goto("/vocab");
    await expect(
      page
        .getByTestId("vocab-deck")
        .filter({ hasText: "Indamukanyo" })
        .getByText("All rested — nothing due."),
    ).toBeVisible({ timeout: 20_000 });
  }).toPass({ timeout: 120_000 });
  await expect(page.getByTestId("review-due")).toBeHidden();
});

/**
 * Journey 5b — the review card says the word out loud, slowly, with the
 * English respelling over it.
 *
 * A deck card is the one place a learner sees a Kinyarwanda word with nothing
 * else on screen to lean on, so it is where the respelling earns its keep.
 */
test("vocab card: respelling above the word, and a slow take of the same clip", async ({
  page,
}) => {
  test.setTimeout(180_000);
  const { token } = await freshUser(page, "j5b-say-it");

  const deck = await getJson<DeckItems>(page.request, "/vocab/decks/greetings", token);
  const first = deck.items[0];
  const guide = fakeRespelling(first.sentence);

  await recordPlaybackRates(page);
  // First card annotated, the rest explicitly null — both paths, one deck.
  await stubPronunciation(page, "**/api/v1/vocab/decks/**", (sentence, i) =>
    i === 0 ? fakeRespelling(sentence) : null,
  );

  await page.goto("/vocab/greetings");
  const card = page.getByTestId("review-card");
  await expect(card).toBeVisible({ timeout: 40_000 });

  const guideParts = card.getByTestId("pronunciation-guide");
  expect((await guideParts.allTextContents()).join(" ")).toBe(guide);
  await expect(card).toContainText(first.sentence);

  const guideBox = (await guideParts.first().boundingBox())!;
  const baseBox = (await card.getByTestId("respell-base").first().boundingBox())!;
  expect(guideBox.y).toBeLessThan(baseBox.y);
  expect(guideBox.y + guideBox.height).toBeLessThanOrEqual(baseBox.y + baseBox.height / 2);

  // The play pair: normal, then the same clip slowed down.
  await card.getByTestId("play-audio").click();
  await card.getByTestId("play-slow").click();
  await expect.poll(() => playedRates(page)).toEqual([1, 0.7]);

  // Next card has no respelling: the card renders clean, nothing reserved.
  await page.getByTestId("reveal-card").click();
  await page.getByTestId("grade-good").click();
  await expect(card.getByTestId("pronunciation-guide")).toHaveCount(0);
  await expect(card.getByTestId("play-slow")).toBeVisible();
});
