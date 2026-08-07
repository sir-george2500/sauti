import type { SessionBlock, SessionBlockKind, SessionPlan } from "./api/types";

/**
 * Pure rendering logic for the Today session card: turns a SessionPlan value
 * object (SPEC §3) into the display model the dashboard renders, including
 * where each block links to.
 */

export interface SessionBlockView {
  tag: string;
  mins: number;
  title: string;
  sub: string;
  kind: SessionBlockKind;
  href: string;
}

export interface SessionPlanView {
  blocks: SessionBlockView[];
  totalMin: number;
  /** e.g. "three short blocks" */
  blockCountLabel: string;
  /** The first block is where "Start session" goes. */
  startHref: string;
}

const COUNT_WORDS = ["no", "one", "two", "three", "four", "five", "six"];

export function blockHref(block: Pick<SessionBlock, "kind" | "ref_id">): string {
  switch (block.kind) {
    case "review":
      // ref_id is the situation deck tag for the due-review block.
      return block.ref_id ? `/vocab/${encodeURIComponent(block.ref_id)}` : "/vocab";
    case "lesson":
      return `/lesson/${block.ref_id}`;
    case "speak":
      return `/practice/pronunciation/${block.ref_id}`;
  }
}

export function sessionPlanView(plan: SessionPlan): SessionPlanView {
  const blocks = plan.blocks.map((b) => ({
    tag: b.tag,
    mins: b.mins,
    title: b.title,
    sub: b.sub,
    kind: b.kind,
    href: blockHref(b),
  }));
  const n = blocks.length;
  const word = COUNT_WORDS[n] ?? String(n);
  return {
    blocks,
    totalMin: plan.total_min,
    blockCountLabel: n === 1 ? "one short block" : `${word} short blocks`,
    startHref: blocks[0]?.href ?? "/roadmap",
  };
}

/** "12 of the last 14 days" */
export function consistencyLabel(activeDays: number, windowDays: number): string {
  return `${activeDays} of the last ${windowDays} days`;
}
