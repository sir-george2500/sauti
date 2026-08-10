import { describe, expect, it } from "vitest";
import { respellPairs, syllables } from "./pronunciation";

describe("respellPairs", () => {
  it("pairs each word with its own respelling", () => {
    expect(respellPairs("Amakuru yawe?", "ah-mah-KOO-roo YAH-weh")).toEqual([
      { base: "Amakuru", guide: "ah-mah-KOO-roo" },
      { base: "yawe?", guide: "YAH-weh" },
    ]);
  });

  it("keeps punctuation on the word it belongs to", () => {
    expect(respellPairs("Mwaramutse!", "mwah-rah-MOOT-seh")).toEqual([
      { base: "Mwaramutse!", guide: "mwah-rah-MOOT-seh" },
    ]);
  });

  it("annotates the whole phrase once when the word counts disagree", () => {
    // Rather than sliding the wrong sound over the wrong word.
    expect(respellPairs("Nitwa Jean.", "NEE-twah")).toEqual([
      { base: "Nitwa Jean.", guide: "NEE-twah" },
    ]);
  });

  it("tolerates ragged whitespace on both sides", () => {
    expect(respellPairs("  Muraho   neza ", " moo-RAH-ho\tNEH-zah ")).toEqual([
      { base: "Muraho", guide: "moo-RAH-ho" },
      { base: "neza", guide: "NEH-zah" },
    ]);
  });

  it("renders nothing extra when there is no guide", () => {
    expect(respellPairs("Mwaramutse!", null)).toBeNull();
    expect(respellPairs("Mwaramutse!", undefined)).toBeNull();
    expect(respellPairs("Mwaramutse!", "")).toBeNull();
    expect(respellPairs("Mwaramutse!", "   ")).toBeNull();
  });

  it("renders nothing extra when there is no sentence to annotate", () => {
    expect(respellPairs("", "mwah-rah-MOOT-seh")).toBeNull();
  });
});

describe("syllables", () => {
  it("flags the capitalised syllable as the stressed one", () => {
    expect(syllables("mwah-rah-MOOT-seh")).toEqual([
      { text: "mwah", stressed: false },
      { text: "rah", stressed: false },
      { text: "MOOT", stressed: true },
      { text: "seh", stressed: false },
    ]);
  });

  it("treats a leading-cap syllable as unstressed (only CAPS carries stress)", () => {
    expect(syllables("Mwah-rah")).toEqual([
      { text: "Mwah", stressed: false },
      { text: "rah", stressed: false },
    ]);
  });

  it("handles a single-syllable guide", () => {
    expect(syllables("NGAY")).toEqual([{ text: "NGAY", stressed: true }]);
  });

  it("never calls a letterless fragment stressed", () => {
    expect(syllables("ee--chee")).toEqual([
      { text: "ee", stressed: false },
      { text: "", stressed: false },
      { text: "chee", stressed: false },
    ]);
  });
});
