import { expect, test, type APIRequestContext } from "@playwright/test";
import { apiLogin, apiRegister, uniqueEmail, PASSWORD } from "./helpers";

/**
 * Email flows — verification banner + link, forgot/reset password.
 *
 * The API runs with SAUTI_FAKE_AI=1, so outbound mail lands in the capturing
 * ConsoleMailer and the test-only GET /__test__/last-mail (mounted in fake-AI
 * mode only) hands the emailed link back to the browser test.
 */

const LAST_MAIL_URL = "http://localhost:8000/__test__/last-mail";

/** Fetch the newest captured mail for `to` and pull out the app link.
 *  Polls briefly: the API sends mail as a post-response background task. */
async function mailedLink(
  request: APIRequestContext,
  to: string,
  pathPrefix: "/verify-email" | "/reset-password",
): Promise<string> {
  for (let attempt = 0; attempt < 20; attempt++) {
    const res = await request.get(`${LAST_MAIL_URL}?to=${encodeURIComponent(to)}`);
    if (res.ok()) {
      const { text } = (await res.json()) as { text: string };
      const link = text.match(/https?:\/\/\S+/g)?.find((u) => u.includes(pathPrefix));
      if (link) return link;
    }
    await new Promise((r) => setTimeout(r, 250));
  }
  throw new Error(`No captured mail with a ${pathPrefix} link for ${to}`);
}

test("register → banner → emailed link verifies → banner gone", async ({ page }) => {
  test.setTimeout(120_000); // several full page loads against the local stack
  const email = uniqueEmail("j-email-verify");
  await apiRegister(page.request, email);
  await apiLogin(page, email);

  // Unverified user sees the nudge banner in the shell.
  await page.goto("/");
  await expect(page.getByTestId("verify-banner")).toBeVisible({ timeout: 30_000 });

  // Resend works and reports success (a second mail is captured).
  await page.getByTestId("resend-verification").click();
  await expect(page.getByTestId("resend-sent")).toBeVisible();

  // Follow the latest emailed link.
  const link = await mailedLink(page.request, email, "/verify-email");
  await page.goto(link);
  await expect(page.getByTestId("verify-success")).toBeVisible();

  // Back in the app the banner is gone (fresh /me on load).
  await page.getByTestId("verify-home").click();
  await expect(page.getByTestId("greeting")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("verify-banner")).toHaveCount(0);
});

test("banner dismiss lasts the session", async ({ page }) => {
  test.setTimeout(120_000);
  const email = uniqueEmail("j-email-dismiss");
  await apiRegister(page.request, email);
  await apiLogin(page, email);

  await page.goto("/");
  await expect(page.getByTestId("verify-banner")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("verify-dismiss").click();
  await expect(page.getByTestId("verify-banner")).toHaveCount(0);

  // Still gone after a reload in the same browser session.
  await page.reload();
  await expect(page.getByTestId("greeting")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("verify-banner")).toHaveCount(0);
});

test("forgot → emailed link → reset → old password dead, new one signs in", async ({
  page,
}) => {
  test.setTimeout(120_000);
  const email = uniqueEmail("j-email-reset");
  const newPassword = "SautiE2e!NewPass1";
  await apiRegister(page.request, email);

  // /login → Forgot password? → request the link.
  await page.goto("/login");
  await page.getByTestId("forgot-link").click();
  await page.waitForURL("**/forgot-password");
  await page.getByTestId("forgot-email").fill(email);
  await page.getByTestId("forgot-submit").click();
  await expect(page.getByTestId("forgot-done")).toBeVisible();

  // Follow the emailed reset link and set the new password.
  const link = await mailedLink(page.request, email, "/reset-password");
  await page.goto(link);
  await page.getByTestId("reset-password").fill(newPassword);
  await page.getByTestId("reset-submit").click();
  await expect(page.getByTestId("reset-success")).toBeVisible();

  // Old password is dead (same generic 401 as any bad credential) …
  const res = await page.request.post("http://localhost:8000/api/v1/auth/login", {
    data: { email, password: PASSWORD },
  });
  expect(res.status()).toBe(401);

  // … and the new one signs in through the UI.
  await page.getByTestId("reset-login-link").click();
  await page.waitForURL("**/login");
  await page.getByTestId("login-email").fill(email);
  await page.getByTestId("login-password").fill(newPassword);
  await page.getByTestId("login-submit").click();
  await expect(page.getByTestId("greeting")).toBeVisible({ timeout: 30_000 });
});
