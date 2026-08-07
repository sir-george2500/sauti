import { expect, test } from "@playwright/test";
import { apiRegister, uniqueEmail, PASSWORD } from "./helpers";

/**
 * Journey 2 — login/logout, auth guard, generic error, silent-refresh reload.
 */

test("auth guard: visiting / logged-out redirects to /login", async ({ page }) => {
  await page.goto("/");
  await page.waitForURL("**/login");
  await expect(page.getByTestId("login-form")).toBeVisible();
});

test("bad password shows one generic error", async ({ page }) => {
  const email = uniqueEmail("j2-badpass");
  await apiRegister(page.request, email);

  await page.goto("/login");
  await page.getByTestId("login-email").fill(email);
  await page.getByTestId("login-password").fill("definitely-not-the-password");
  await page.getByTestId("login-submit").click();

  await expect(page.getByTestId("login-error")).toBeVisible();
  await expect(page.getByTestId("login-error")).toContainText(
    "That email and password don't match",
  );
  // Still on the login page, not signed in.
  await expect(page).toHaveURL(/\/login/);
});

test("login → session survives reload (silent refresh) → logout revokes it", async ({
  page,
}) => {
  test.setTimeout(120_000); // several remote-DB page loads
  const email = uniqueEmail("j2-session");
  await apiRegister(page.request, email);

  // UI login.
  await page.goto("/login");
  await page.getByTestId("login-email").fill(email);
  await page.getByTestId("login-password").fill(PASSWORD);
  await page.getByTestId("login-submit").click();
  await page.waitForURL(/\/$/);
  await expect(page.getByTestId("greeting")).toBeVisible({ timeout: 30_000 });

  // Hard reload: the in-memory access token is gone; the app must silently
  // refresh from the httpOnly cookie and stay signed in.
  await page.reload();
  await expect(page.getByTestId("greeting")).toBeVisible({ timeout: 30_000 });

  // Logout revokes the refresh family and returns to /login.
  await page.getByTestId("sign-out").click();
  await page.waitForURL("**/login");

  // The guard now bounces an authed route back to /login.
  await page.goto("/");
  await page.waitForURL("**/login");
  await expect(page.getByTestId("login-form")).toBeVisible();
});
