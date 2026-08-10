import { createElement, Fragment, type ReactNode } from "react";
import { respellPairs, syllables } from "@/lib/pronunciation";

/**
 * Kinyarwanda with its English respelling floated above it.
 *
 *   mwah-rah-MOOT-seh
 *      Mwaramutse
 *
 * Semantics first: this is `<ruby>` with an `<rt>` annotation, which is
 * literally the element for "how this is pronounced". Screen readers announce
 * base and annotation, the guide sits over the word by default (no absolute
 * positioning to fight with), and each word carries its own annotation so a
 * longer line still wraps at the spaces.
 *
 * Typography (see `.respell` in globals.css): the Kinyarwanda stays the hero —
 * full serif size, full ink. The guide is a whisper: mono face, ~10–12.5px
 * whatever the base size, letterspaced so the hyphens read as syllable breaks,
 * in the faintest ink — with the CAPS syllable a shade darker and heavier so
 * the stress is the one thing that pops out of the whisper.
 *
 * With no guide (the common case while the field rolls out) this renders the
 * exact same element it always did, with no wrapper, no placeholder and no
 * reserved space.
 */
export function Respelled({
  text,
  guide,
  as = "p",
  className = "",
  testid = "pronunciation-guide",
  children,
}: {
  /** The Kinyarwanda line. */
  text: string;
  /** `item.pronunciation` — absent/null for most items today. */
  guide?: string | null;
  as?: "p" | "span" | "div";
  className?: string;
  testid?: string;
  /** Rendered after the line, inside the same element (e.g. quotation marks). */
  children?: ReactNode;
}) {
  const pairs = respellPairs(text, guide);

  if (!pairs) {
    return createElement(as, { className: className || undefined }, text, children);
  }

  return createElement(
    as,
    { className: `respell ${className}`.trim() },
    <ruby>
      {pairs.map((pair, i) => (
        <Fragment key={`${pair.base}-${i}`}>
          {i > 0 ? " " : null}
          <span data-testid="respell-base">{pair.base}</span>
          <rt data-testid={testid}>
            {syllables(pair.guide).map((syllable, s) => (
              <Fragment key={s}>
                {s > 0 ? <span className="respell-break">-</span> : null}
                <span className={syllable.stressed ? "respell-stress" : undefined}>
                  {syllable.text}
                </span>
              </Fragment>
            ))}
          </rt>
        </Fragment>
      ))}
    </ruby>,
    children,
  );
}
