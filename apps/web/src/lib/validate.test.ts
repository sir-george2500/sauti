import { describe, expect, it } from "vitest";
import { validateEmail, validateLoginPassword, validatePassword } from "./validate";

describe("validateEmail", () => {
  it("requires a value", () => {
    expect(validateEmail("")).toMatch(/required/i);
    expect(validateEmail("   ")).toMatch(/required/i);
  });
  it("rejects malformed addresses", () => {
    for (const bad of ["ange", "ange@", "@sauti.rw", "ange@sauti", "a b@sauti.rw"]) {
      expect(validateEmail(bad)).not.toBeNull();
    }
  });
  it("accepts normal addresses (and trims)", () => {
    expect(validateEmail("ange@sauti.rw")).toBeNull();
    expect(validateEmail("  ange+test@mail.example.com  ")).toBeNull();
  });
});

describe("validatePassword", () => {
  it("requires a value", () => {
    expect(validatePassword("")).toMatch(/required/i);
  });
  it("enforces the 8-char minimum", () => {
    expect(validatePassword("short7!")).toMatch(/8 characters/);
    expect(validatePassword("longenough")).toBeNull();
  });
  it("rejects common passwords case-insensitively", () => {
    expect(validatePassword("password123")).toMatch(/common/i);
    expect(validatePassword("PASSWORD123")).toMatch(/common/i);
  });
});

describe("validateLoginPassword", () => {
  it("only requires non-empty (no length rule for existing accounts)", () => {
    expect(validateLoginPassword("")).toMatch(/required/i);
    expect(validateLoginPassword("x")).toBeNull();
  });
});
