import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Respelled } from "./PronunciationGuide";

describe("Respelled", () => {
  it("puts the respelling in a ruby annotation over the word", () => {
    const { container } = render(
      <Respelled text="Mwaramutse!" guide="mwah-rah-MOOT-seh" className="ky text-lg" />,
    );

    const guide = screen.getByTestId("pronunciation-guide");
    expect(guide.tagName).toBe("RT");
    expect(guide).toHaveTextContent("mwah-rah-MOOT-seh");
    // The annotation is inside the ruby, so it is genuinely attached to the
    // word rather than being a separate line that happens to sit above it.
    expect(guide.closest("ruby")).not.toBeNull();
    expect(screen.getByTestId("respell-base")).toHaveTextContent("Mwaramutse!");
    expect(container.querySelector(".respell")).not.toBeNull();
  });

  it("marks the capitalised syllable so the stress can be styled", () => {
    const { container } = render(
      <Respelled text="Mwaramutse!" guide="mwah-rah-MOOT-seh" />,
    );
    const stressed = container.querySelectorAll(".respell-stress");
    expect(stressed).toHaveLength(1);
    expect(stressed[0]).toHaveTextContent("MOOT");
  });

  it("gives every word of a sentence its own annotation", () => {
    render(<Respelled text="Amakuru yawe?" guide="ah-mah-KOO-roo YAH-weh" />);
    const guides = screen.getAllByTestId("pronunciation-guide");
    expect(guides.map((g) => g.textContent)).toEqual(["ah-mah-KOO-roo", "YAH-weh"]);
    expect(screen.getAllByTestId("respell-base").map((b) => b.textContent)).toEqual([
      "Amakuru",
      "yawe?",
    ]);
  });

  it("renders the plain line with no extra markup when there is no guide", () => {
    const { container } = render(
      <Respelled text="Mwaramutse!" guide={null} className="ky text-lg" />,
    );
    expect(screen.queryByTestId("pronunciation-guide")).toBeNull();
    expect(container.querySelector("ruby")).toBeNull();
    expect(container.querySelector(".respell")).toBeNull();
    const p = container.querySelector("p")!;
    expect(p.className).toBe("ky text-lg");
    expect(p).toHaveTextContent("Mwaramutse!");
  });

  it("honours the element it is asked to be", () => {
    const { container } = render(
      <Respelled as="span" text="Muraho" guide="moo-RAH-ho" />,
    );
    expect(container.querySelector("span.respell")).not.toBeNull();
  });
});
