import { expect, test } from "@playwright/test";
import { execFileSync } from "child_process";
import path from "path";
import { allItems, freshUser, getJson, type RoadmapPayload } from "./helpers";

/**
 * Journey — "Hear yourself change" recordings archive + new scenario pack.
 *
 * 1. The two new seeded scenarios (Urugendo rwa moto A1, Gusura umuryango A2)
 *    are served by GET /scenarios with persona opening lines and render in
 *    the conversation UI.
 * 2. Two real pronunciation takes (fake-device MediaRecorder, same flow as
 *    pronunciation.spec.ts) land in the Progress page's archive: first vs
 *    latest recording, playable, with the design's caption line.
 */

interface Scenario {
  id: string;
  title: string;
  min_cefr: string;
  goals: string[];
  persona: {
    name: string;
    role: string;
    opening_line?: { ky: string; en: string } | null;
  };
}

interface RecordingPayload {
  id: string;
  ts: string;
  day_number: number;
  item_sentence: string;
  audio_url: string;
  score: number;
}

const API_DIR = path.resolve(__dirname, "../../../services/api");

/** Place a user at a CEFR level directly — see helpers/set_placed_level.py. */
function setPlacedLevel(email: string, cefr: string): void {
  const script = path.join(__dirname, "helpers", "set_placed_level.py");
  const out = execFileSync("uv", ["run", "python", script, email, cefr], {
    cwd: API_DIR,
    encoding: "utf-8",
    env: {
      ...process.env,
      // Same database the API under test is on (local e2e Postgres).
      POSTGRES_URL: "postgresql://postgres:sauti-e2e@localhost:55432/postgres",
    },
  });
  expect(parseInt(out.trim(), 10)).toBe(1);
}

test("new scenarios: served with opening lines, render in the conversation UI", async ({
  page,
}) => {
  test.setTimeout(120_000);
  const { email, token } = await freshUser(page, "j-arch-scen");

  // A fresh user is A1: both A1 scenarios are listed, each with a scripted
  // opening line (served without an LLM call); the A2 family visit is not.
  let scenarios = await getJson<Scenario[]>(page.request, "/scenarios", token);
  const titles = scenarios.map((s) => s.title);
  expect(titles).toContain("Kimironko market run");
  expect(titles).toContain("Urugendo rwa moto");
  expect(titles).not.toContain("Gusura umuryango");
  for (const s of scenarios) {
    expect(s.persona.opening_line?.ky, `${s.title} opening_line.ky`).toBeTruthy();
    expect(s.persona.opening_line?.en, `${s.title} opening_line.en`).toBeTruthy();
  }

  const moto = scenarios.find((s) => s.title === "Urugendo rwa moto")!;
  expect(moto.persona.name).toBe("Eric");
  expect(moto.persona.opening_line!.ky).toBe("Muraho! Urashaka kujya he?");
  expect(moto.goals).toContain("agree on a fare");

  // The moto scenario renders in the conversation UI.
  await page.goto(`/practice/conversation/${moto.id}`);
  await expect(page.getByTestId("persona-card")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("persona-card")).toContainText("Eric · moto driver");
  await expect(page.getByTestId("umuco-tip")).toContainText("Agree the fare");

  // Placed at A2, the family visit joins the list and renders too.
  setPlacedLevel(email, "A2");
  scenarios = await getJson<Scenario[]>(page.request, "/scenarios", token);
  const family = scenarios.find((s) => s.title === "Gusura umuryango")!;
  expect(family.min_cefr).toBe("A2");
  expect(family.persona.name).toBe("Mama Chantal");
  expect(family.persona.opening_line!.ky).toContain("Murakaza neza mu rugo rwacu");

  await page.goto(`/practice/conversation/${family.id}`);
  await expect(page.getByTestId("persona-card")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("persona-card")).toContainText("Mama Chantal");
});

test("recordings archive: empty state before any take", async ({ page }) => {
  await freshUser(page, "j-arch-empty");
  await page.goto("/progress");
  const archive = page.getByTestId("recordings-archive");
  await expect(archive).toBeVisible({ timeout: 40_000 });
  await expect(archive).toContainText("Hear yourself change");
  await expect(archive).toContainText("Your first recording will live here");
  await expect(page.getByTestId("recording-first")).toHaveCount(0);
});

test("recordings archive: two takes surface as first vs latest, playable", async ({
  page,
}) => {
  test.setTimeout(180_000);
  const { token } = await freshUser(page, "j-arch-rec");

  const roadmap = await getJson<RoadmapPayload>(page.request, "/roadmap", token);
  const item = allItems(roadmap)[0]; // "Mwaramutse!"

  // Two real takes through the pronunciation UI (fake media device).
  await page.goto(`/practice/pronunciation/${item.id}`);
  const record = page.getByTestId("record-button");
  await expect(record).toContainText("Record take 1", { timeout: 40_000 });
  for (const take of [1, 2]) {
    await record.click();
    await expect(record).toHaveAttribute("aria-pressed", "true");
    await page.waitForTimeout(900); // capture a short take from the fake mic
    await record.click(); // stop → upload → score → attempt
    await expect(record).toContainText(`Record take ${take + 1}`, { timeout: 30_000 });
  }

  // The API keeps both, chronological, day 1 (same-day takes). The speak
  // attempt posts fire-and-forget after scoring, so poll until the last one
  // lands (same pattern as the vocab review spec).
  let recordings: RecordingPayload[] = [];
  await expect(async () => {
    recordings = await getJson<RecordingPayload[]>(
      page.request,
      "/progress/recordings",
      token,
    );
    expect(recordings).toHaveLength(2);
  }).toPass({ timeout: 30_000 });
  expect(recordings[0].day_number).toBe(1);
  expect(recordings[1].day_number).toBe(1);
  expect(recordings[0].item_sentence).toBe(item.sentence);
  expect(new Date(recordings[0].ts) <= new Date(recordings[1].ts)).toBe(true);
  // The resolved audio_url is directly fetchable (public, like an <audio> src).
  const audioRes = await page.request.get(recordings[0].audio_url);
  expect(audioRes.status()).toBe(200);
  expect(audioRes.headers()["content-type"]).toContain("audio/");

  // Progress renders the archive: first vs latest, captioned per the design.
  await page.goto("/progress");
  const archive = page.getByTestId("recordings-archive");
  await expect(archive).toBeVisible({ timeout: 40_000 });
  const first = page.getByTestId("recording-first");
  const latest = page.getByTestId("recording-latest");
  await expect(first).toBeVisible();
  await expect(latest).toBeVisible();
  await expect(first).toContainText("Week 1");
  await expect(first).toContainText("Mwaramutse");
  await expect(latest).toContainText("Day 1");
  await expect(archive).toContainText("This is why you keep the recordings.");

  // The first recording plays through the UI control.
  const play = page.getByTestId("recording-play").first();
  await play.click();
  await expect(play).toHaveAttribute("aria-label", /Pause/);
});
