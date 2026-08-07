/**
 * Proverb of the day. No API endpoint exists for proverbs (SPEC §5), so the
 * dashboard rotates a small curated list client-side by day of year — noted
 * in docs/frontend-notes.md.
 */

export interface Proverb {
  ky: string;
  en: string;
}

export const PROVERBS: readonly Proverb[] = [
  {
    ky: "Buhoro buhoro ni rwo rugendo.",
    en: "Slowly, slowly — that is the journey.",
  },
  {
    ky: "Akebo kajya iwa Mugarura.",
    en: "The basket returns to Mugarura — kindness comes back.",
  },
  {
    ky: "Uwanze gutera intimba ntiyica isazi.",
    en: "Who fears small stings will never swat the fly.",
  },
  {
    ky: "Inzira ntibwira umugenzi.",
    en: "The path does not warn the traveller.",
  },
  {
    ky: "Uko wagiye ni ko ugaruka.",
    en: "As you set out, so you return.",
  },
];

export function proverbOfTheDay(date: Date = new Date()): Proverb {
  const start = Date.UTC(date.getFullYear(), 0, 0);
  const dayOfYear = Math.floor((Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()) - start) / 86400000);
  return PROVERBS[dayOfYear % PROVERBS.length];
}
