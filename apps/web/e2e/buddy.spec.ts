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

  // Every fetch of a synthesized clip, so playback can be asserted headless
  // (real speakers are not a thing in CI).
  const clipRequests: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/speech/audio/")) clipRequests.push(request.url());
  });

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

  // --- The reply is speakable: a real clip, really fetched ------------------
  // Against the real (stub-voice) backend: the reply frame promised a clip and
  // the follow-up frame delivered a playable one, so the control leaves
  // `pending` and pressing it goes and gets the audio.
  const play = page.getByTestId("buddy-play").last();
  await expect(play).toBeVisible({ timeout: 30_000 });
  await expect(play).toHaveAttribute("data-state", /ready|playing/, { timeout: 30_000 });
  if ((await play.getAttribute("data-state")) === "playing") await play.click(); // it autoplayed
  await play.click();
  await expect
    .poll(() => clipRequests.length, { timeout: 15_000, message: "the clip was fetched" })
    .toBeGreaterThan(0);

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

/**
 * Journey — Mwarimu's voice.
 *
 * The frames are mocked here (page.routeWebSocket) so the *timing* is ours:
 * the reply lands first and its clip a beat later, which is exactly the shape
 * the real backend has (text now, synthesis in a second or two) and the only
 * way to see `pending` reliably. The clip itself is served by the test, so
 * "did it actually play?" is a request assertion rather than a guess about
 * headless audio hardware.
 */

/** A few seconds of 16-bit silence — long enough to catch mid-playback. */
function wavBytes(seconds = 4, rate = 8000): Buffer {
  const data = Buffer.alloc(seconds * rate * 2);
  const header = Buffer.alloc(44);
  header.write("RIFF", 0);
  header.writeUInt32LE(36 + data.length, 4);
  header.write("WAVE", 8);
  header.write("fmt ", 12);
  header.writeUInt32LE(16, 16);
  header.writeUInt16LE(1, 20); // PCM
  header.writeUInt16LE(1, 22); // mono
  header.writeUInt32LE(rate, 24);
  header.writeUInt32LE(rate * 2, 28);
  header.writeUInt16LE(2, 32);
  header.writeUInt16LE(16, 34);
  header.write("data", 36);
  header.writeUInt32LE(data.length, 40);
  return Buffer.concat([header, data]);
}

test("study buddy voice: pending → ready → playing, and a speaker that remembers", async ({
  page,
}) => {
  test.setTimeout(120_000);
  await freshUser(page, "j-buddy-voice");

  const CLIP = "http://localhost:3000/e2e-mwarimu-clip.wav";
  const clipRequests: string[] = [];
  await page.route(CLIP, async (route) => {
    clipRequests.push(route.request().url());
    await route.fulfill({ status: 200, contentType: "audio/wav", body: wavBytes() });
  });

  let turn = 0;
  await page.routeWebSocket(/\/ws\/buddy/, (ws) => {
    ws.onMessage(async () => {
      const id = `clip-${++turn}`;
      ws.send(JSON.stringify({ type: "buddy", id, text: "Ndagusuhuje!", gloss: "I greet you!" }));
      // Junk the widget must swallow: a clip for a turn nobody has, and a URL
      // no browser should ever be handed.
      ws.send(JSON.stringify({ type: "buddy_audio", id: "no-such-turn", audio_url: CLIP }));
      ws.send(JSON.stringify({ type: "buddy_audio", id, audio_url: "javascript:alert(1)" }));
      // Synthesis takes a beat, exactly like the real thing.
      await new Promise((resolve) => setTimeout(resolve, 1500));
      ws.send(JSON.stringify({ type: "buddy_audio", id, audio_url: CLIP }));
    });
  });

  await page.goto("/");
  await page.getByTestId("buddy-fab").click({ timeout: 30_000 });
  const toggle = page.getByTestId("buddy-sound-toggle");
  await expect(toggle, "voice is on out of the box").toHaveAttribute("data-on", "true");

  // --- The reply arrives silent, then finds its voice ----------------------
  await page.getByTestId("buddy-input").fill("Muraho!");
  await page.getByTestId("buddy-send").click();
  const play = page.getByTestId("buddy-play");
  await expect(play).toBeVisible({ timeout: 30_000 });
  await expect(play, "waiting on synthesis, not clickable").toHaveAttribute(
    "data-state",
    "pending",
  );
  expect(clipRequests, "nothing playable yet — nothing fetched").toHaveLength(0);

  // The clip lands: the control wakes up and, with sound on, speaks by itself.
  await expect(play).toHaveAttribute("data-state", /ready|playing/, { timeout: 20_000 });
  await expect
    .poll(() => clipRequests.length, { timeout: 15_000, message: "the newest reply autoplays" })
    .toBeGreaterThan(0);
  await expect(play).toHaveAttribute("data-state", "playing", { timeout: 10_000 });

  // --- Tap to stop, tap to play again --------------------------------------
  await play.click();
  await expect(play).toHaveAttribute("data-state", "ready");
  await play.click();
  await expect(play).toHaveAttribute("data-state", "playing");

  // --- Closing the panel takes the voice with it ---------------------------
  await page.keyboard.press("Escape");
  await expect(page.getByTestId("buddy-panel")).toHaveCount(0);
  await page.getByTestId("buddy-fab").click();
  await expect(play, "reopened quiet — the clip was stopped, not left running").toHaveAttribute(
    "data-state",
    "ready",
  );

  // --- The speaker toggle survives a reload --------------------------------
  await toggle.click();
  await expect(toggle).toHaveAttribute("data-on", "false");
  await page.reload();
  await page.getByTestId("buddy-fab").click({ timeout: 30_000 });
  await expect(page.getByTestId("buddy-sound-toggle")).toHaveAttribute("data-on", "false");
  // The conversation (and its clip) came back with it — still playable by hand.
  await expect(page.getByTestId("buddy-play")).toHaveAttribute("data-state", "ready");

  const fetchedBefore = clipRequests.length;
  await page.getByTestId("buddy-input").fill("Ongera!");
  await page.getByTestId("buddy-send").click();
  await expect(page.getByTestId("buddy-play").last()).toHaveAttribute("data-state", "ready", {
    timeout: 20_000,
  });
  expect(clipRequests.length, "muted: the new reply waits to be tapped").toBe(fetchedBefore);

  // …and back on again, still remembered.
  await page.getByTestId("buddy-sound-toggle").click();
  await page.reload();
  await page.getByTestId("buddy-fab").click({ timeout: 30_000 });
  await expect(page.getByTestId("buddy-sound-toggle")).toHaveAttribute("data-on", "true");
});
