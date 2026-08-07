import { defineConfig, devices } from "@playwright/test";
import path from "path";

/**
 * E2E config (docs/SPEC.md §7 — e2e is the acceptance bar).
 *
 * Boots BOTH servers via the webServer block:
 *  - the FastAPI backend on :8000 with SAUTI_FAKE_AI=1 (scripted FakeLlmClient +
 *    stub speech — no paid APIs) and a raised auth rate limit (the whole suite
 *    shares one IP bucket otherwise; see services/api/src/sauti/rate_limit.py),
 *  - the Next dev server on :3000.
 *
 * Prerequisites (already-idempotent, run once before the first e2e run):
 *   cd services/api && uv run alembic upgrade head && uv run python -m sauti.seed
 *
 * NOTE on reuseExistingServer: if you start the API yourself, it MUST be started
 * with SAUTI_FAKE_AI=1 and RATE_LIMIT_AUTH_MAX=100000 or the conversation specs
 * (scripted replies) and parallel auth flows will fail:
 *   cd services/api && SAUTI_FAKE_AI=1 RATE_LIMIT_AUTH_MAX=100000 \
 *     uv run uvicorn sauti.main:app --port 8000
 *
 * The fake-media flags give MediaRecorder a real (silent-ish) audio device so
 * the pronunciation record flow runs headless end-to-end.
 */

const API_DIR = path.resolve(__dirname, "../../services/api");

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  // The shared Postgres is remote (~300 ms RTT): multi-query endpoints take
  // seconds, so parallelism stays low. Slow journeys raise their own
  // test.setTimeout / per-assert timeouts instead of inflating the globals,
  // and maxFailures stops a broken run early instead of letting it hang.
  workers: 2,
  maxFailures: 5,
  reporter: [["line"], ["html", { open: "never" }]],
  timeout: 60_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        permissions: ["microphone"],
        launchOptions: {
          args: [
            "--use-fake-ui-for-media-stream",
            "--use-fake-device-for-media-stream",
          ],
        },
      },
    },
  ],
  webServer: [
    {
      command: "uv run uvicorn sauti.main:app --port 8000",
      cwd: API_DIR,
      url: "http://localhost:8000/healthz",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        SAUTI_FAKE_AI: "1",
        RATE_LIMIT_AUTH_MAX: "100000",
      },
    },
    {
      command: "pnpm dev",
      url: "http://localhost:3000",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        NEXT_PUBLIC_API_BASE_URL:
          process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1",
      },
    },
  ],
});
