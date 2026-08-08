"use client";

import { useSaveToNotebook } from "@/lib/notebook";

/**
 * Small bookmark toggle on lesson rows, vocab cards and pronunciation —
 * one tap keeps the item in the notebook (Ikaye) with its gloss. Silent
 * success: the mark just fills; already-saved stays filled and inert.
 */
export function SaveToNotebook({ itemId, className = "" }: { itemId: string; className?: string }) {
  const { saved, save, saving } = useSaveToNotebook(itemId);

  return (
    <button
      type="button"
      data-testid="save-to-notebook"
      data-saved={saved}
      aria-pressed={saved}
      aria-label={saved ? "Saved in your notebook" : "Save to notebook"}
      title={saved ? "In your notebook (Ikaye)" : "Save to notebook"}
      onClick={save}
      disabled={saving}
      className={`inline-flex h-[34px] w-[34px] shrink-0 items-center justify-center rounded-full transition-colors ${
        saved
          ? "cursor-default text-gold-text"
          : "cursor-pointer text-ink-faint hover:bg-accent-soft hover:text-accent"
      } disabled:opacity-60 ${className}`}
    >
      {saved ? (
        <svg viewBox="0 0 16 16" className="h-[15px] w-[15px] fill-current" aria-hidden>
          <path d="M4 1.5h8a1 1 0 0 1 1 1v12l-5-3.2-5 3.2v-12a1 1 0 0 1 1-1Z" />
        </svg>
      ) : (
        <svg
          viewBox="0 0 16 16"
          className="h-[15px] w-[15px] fill-none stroke-current"
          strokeWidth="1.5"
          aria-hidden
        >
          <path d="M4 1.75h8a.75.75 0 0 1 .75.75v11.6L8 11l-4.75 3.1V2.5A.75.75 0 0 1 4 1.75Z" />
        </svg>
      )}
    </button>
  );
}
