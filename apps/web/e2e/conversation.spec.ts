import { expect, test } from "@playwright/test";
import { freshUser, getJson } from "./helpers";

interface Scenario {
  id: string;
  title: string;
  persona: {
    name: string;
    role: string;
    opening_line?: { ky?: string; en?: string };
  };
  goals: string[];
  umuco_tip?: string | null;
}

/**
 * Journey 6 — Conversation over WS with the scripted FakeLlmClient:
 * persona + goals → send text → partner reply (gloss toggle) → coach notes
 * per the server-side policy (praise first, ≤1 fix, no fix on turn 1) →
 * goal marked when the learner asks a price.
 */
test("Kimironko market conversation: partner, gloss, coach policy, goal", async ({
  page,
}) => {
  test.setTimeout(180_000); // WS turns persist several rows on the remote DB
  const { token } = await freshUser(page, "j6-convo");

  const scenarios = await getJson<Scenario[]>(page.request, "/scenarios", token);
  const kimironko = scenarios.find((s) => s.title.includes("Kimironko"))!;
  expect(kimironko).toBeTruthy();

  await page.goto(`/practice/conversation/${kimironko.id}`);

  // Persona card + umuco tip + goals.
  await expect(page.getByTestId("persona-card")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("persona-card")).toContainText("Mukamana");
  await expect(page.getByTestId("persona-card")).toContainText("vegetable vendor");
  await expect(page.getByTestId("umuco-tip")).toBeVisible();
  await expect(page.getByTestId("goal")).toHaveCount(kimironko.goals.length);
  await expect(page.getByTestId("hint-chip").first()).toBeVisible();

  // Scenarios with persona.opening_line greet first: a scripted (zero-LLM)
  // partner frame arrives on connect, before any learner input.
  const openerKy = kimironko.persona.opening_line?.ky;
  if (openerKy) {
    await expect(
      page.getByTestId("partner-message").filter({ hasText: openerKy }),
    ).toBeVisible({ timeout: 30_000 });
  }

  // Send button enables once the WS is connected.
  const send = page.getByTestId("chat-send");
  await page.getByTestId("chat-input").fill("Muraho! Amakuru?");
  await expect(send).toBeEnabled();
  await send.click();

  await expect(page.getByTestId("user-message")).toContainText("Muraho! Amakuru?");

  // Scripted partner reply for a greeting turn (an opener may precede it, so
  // select by text rather than position).
  const partner = page
    .getByTestId("partner-message")
    .filter({ hasText: "Muraho neza!" });
  await expect(partner).toBeVisible({ timeout: 30_000 });

  // Gloss toggle: shows "gloss", click reveals the EN line.
  const gloss = partner.getByTestId("gloss-toggle");
  await expect(gloss).toHaveText("gloss");
  await gloss.click();
  await expect(gloss).toContainText("What would you like at the market?");

  // Coach on turn 1: praise only — the policy never fixes the first turn.
  await expect(page.getByTestId("coach-note")).toHaveCount(1, { timeout: 20_000 });
  await expect(page.getByTestId("coach-note")).toContainText("Byiza cyane!");

  // Turn 2: ask a price → goal frame + partner price reply + praise-first fix.
  await page.getByTestId("chat-input").fill("Ni angahe?");
  await send.click();

  await expect(
    page.getByTestId("partner-message").filter({ hasText: "Ikilo cy'inyanya" }),
  ).toBeVisible({ timeout: 30_000 });

  // The "ask a price" goal is marked.
  const priceGoal = page.getByTestId("goal").filter({ hasText: "ask a price" });
  await expect(priceGoal).toContainText("✓");
  const greetGoal = page.getByTestId("goal").filter({ hasText: "greet the vendor" });
  await expect(greetGoal).toContainText("○");

  // Coach policy fired: praise first, then exactly one fix ("Greeting form").
  await expect(page.getByTestId("coach-note")).toHaveCount(3, { timeout: 20_000 });
  const fixNote = page.getByTestId("coach-note").filter({ hasText: "Greeting form" });
  await expect(fixNote).toBeVisible();
  await expect(fixNote).toContainText('Try opening with "Muraho!"');
});
