"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { addNotebookEntry, getNotebook } from "@/lib/api/endpoints";
import type { NotebookEntry } from "@/lib/api/types";

/**
 * Notebook (Ikaye) save-state — shared by every "save to notebook" bookmark.
 *
 * The notebook is fetched ONCE per session (staleTime: Infinity on the shared
 * ["notebook"] key); saved-ness is derived by matching item_id. Mutations
 * append into the same cache, so a save on the lesson page is instantly
 * "filled" on the vocab and pronunciation screens too. The /notebook page
 * itself refetches on mount for freshness.
 */

export const NOTEBOOK_KEY = ["notebook"] as const;

/** Item ids already saved — pure, unit-tested. */
export function savedItemIds(entries: NotebookEntry[] | undefined): Set<string> {
  const ids = new Set<string>();
  for (const e of entries ?? []) {
    if (e.item_id) ids.add(e.item_id);
  }
  return ids;
}

/** Prepend a fresh entry, replacing any previous entry for the same item. */
export function withEntry(
  entries: NotebookEntry[] | undefined,
  entry: NotebookEntry,
): NotebookEntry[] {
  const rest = (entries ?? []).filter(
    (e) => e.id !== entry.id && !(entry.item_id && e.item_id === entry.item_id),
  );
  return [entry, ...rest];
}

export function useNotebook(options: { refetchOnMount?: boolean } = {}) {
  return useQuery({
    queryKey: NOTEBOOK_KEY,
    queryFn: getNotebook,
    staleTime: Infinity,
    refetchOnMount: options.refetchOnMount ?? false,
  });
}

/**
 * Save-state for one curriculum item: `saved` once the item is in the
 * notebook (session cache), `save()` writes it (item snapshot server-side).
 */
export function useSaveToNotebook(itemId: string) {
  const queryClient = useQueryClient();
  const notebook = useNotebook();
  const saved = savedItemIds(notebook.data).has(itemId);

  const mutation = useMutation({
    mutationFn: () => addNotebookEntry({ item_id: itemId }),
    onSuccess: (entry) => {
      queryClient.setQueryData<NotebookEntry[]>(NOTEBOOK_KEY, (prev) =>
        withEntry(prev, entry),
      );
    },
  });

  const save = () => {
    if (saved || mutation.isPending) return;
    mutation.mutate();
  };

  return { saved, save, saving: mutation.isPending };
}
