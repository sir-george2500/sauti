// Client-side field validation for the auth forms. Mirrors the backend's
// rules (valid email, password ≥ 8 chars, common-password denylist) so the
// user hears about problems while typing, not after a round-trip.

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

// Small mirror of the backend denylist — the server remains the authority.
const COMMON_PASSWORDS = new Set([
  "password",
  "password1",
  "password123",
  "12345678",
  "123456789",
  "qwerty123",
  "11111111",
  "letmein1",
]);

export function validateEmail(email: string): string | null {
  const v = email.trim();
  if (v.length === 0) return "Email is required.";
  if (!EMAIL_RE.test(v)) return "That doesn't look like an email address.";
  return null;
}

export function validatePassword(password: string): string | null {
  if (password.length === 0) return "Password is required.";
  if (password.length < 8) return "Use at least 8 characters.";
  if (COMMON_PASSWORDS.has(password.toLowerCase()))
    return "That password is too common — pick something more personal.";
  return null;
}

/** Login only needs a non-empty password — no length rule on existing accounts. */
export function validateLoginPassword(password: string): string | null {
  return password.length === 0 ? "Password is required." : null;
}
