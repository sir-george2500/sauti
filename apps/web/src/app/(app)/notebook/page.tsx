"use client";

import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  addNotebookEntry,
  deleteNotebookEntry,
  updateNotebookEntry,
} from "@/lib/api/endpoints";
import { NOTEBOOK_KEY, useNotebook, withEntry } from "@/lib/notebook";
import { AudioControls } from "@/components/AudioButton";
import {
  btnGhost,
  btnPrimary,
  Card,
  CardLabel,
  ErrorNote,
  Kicker,
  Lead,
  LoadingNote,
  PageTitle,
} from "@/components/ui";
import type { NotebookEntry } from "@/lib/api/types";

const inputCls =
  "w-full rounded-btn border border-line-strong bg-card px-3.5 py-2.5 text-sm text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none";

function keptOn(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "long" });
}

function EntryRow({ entry }: { entry: NotebookEntry }) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [noteDraft, setNoteDraft] = useState(entry.note ?? "");
  const [confirming, setConfirming] = useState(false);

  const update = useMutation({
    mutationFn: (note: string) =>
      updateNotebookEntry(entry.id, { note: note.trim() || null }),
    onSuccess: (fresh) => {
      queryClient.setQueryData<NotebookEntry[]>(NOTEBOOK_KEY, (prev) =>
        (prev ?? []).map((e) => (e.id === fresh.id ? fresh : e)),
      );
      setEditing(false);
    },
  });

  const remove = useMutation({
    mutationFn: () => deleteNotebookEntry(entry.id),
    onSuccess: () => {
      queryClient.setQueryData<NotebookEntry[]>(NOTEBOOK_KEY, (prev) =>
        (prev ?? []).filter((e) => e.id !== entry.id),
      );
    },
  });

  return (
    <li
      data-testid="notebook-entry"
      className="flex items-start gap-3.5 border-b border-line py-4 last:border-b-0 last:pb-0 first:pt-0"
    >
      {entry.item_id ? (
        <AudioControls
          itemId={entry.item_id}
          src={entry.audio_url}
          size="sm"
          testid="notebook-play"
          label={`Play “${entry.text}”`}
          className="mt-0.5"
        />
      ) : (
        <span
          aria-hidden
          className="mt-0.5 flex h-[34px] w-[34px] flex-none items-center justify-center text-gold-text"
        >
          <svg viewBox="0 0 16 16" className="h-[15px] w-[15px] fill-current">
            <path d="M4 1.5h8a1 1 0 0 1 1 1v12l-5-3.2-5 3.2v-12a1 1 0 0 1 1-1Z" />
          </svg>
        </span>
      )}

      <div className="min-w-0 flex-1">
        <p className="ky text-lg leading-snug font-semibold">{entry.text}</p>
        {entry.gloss ? (
          <p className="mt-0.5 text-[12.5px] text-ink-soft">{entry.gloss}</p>
        ) : null}

        {editing ? (
          <div className="mt-2.5 grid gap-2">
            <textarea
              data-testid="notebook-note-input"
              value={noteDraft}
              onChange={(e) => setNoteDraft(e.target.value)}
              rows={2}
              maxLength={2000}
              placeholder="Why this word stuck with you…"
              className={inputCls}
            />
            <div className="flex gap-2">
              <button
                type="button"
                data-testid="notebook-save"
                onClick={() => update.mutate(noteDraft)}
                disabled={update.isPending}
                className={btnPrimary}
              >
                {update.isPending ? "Keeping…" : "Save note"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setEditing(false);
                  setNoteDraft(entry.note ?? "");
                }}
                className={btnGhost}
              >
                Cancel
              </button>
            </div>
          </div>
        ) : entry.note ? (
          <p className="mt-1.5 rounded-lg bg-amber-soft px-2.5 py-1.5 text-[13px] text-amber-deep">
            {entry.note}
          </p>
        ) : null}

        <div className="mt-1.5 flex items-center gap-3">
          <span className="font-mono text-[10px] text-ink-faint uppercase">
            Kept {keptOn(entry.created_at)}
          </span>
          {!editing ? (
            <button
              type="button"
              data-testid="notebook-edit-note"
              onClick={() => {
                setNoteDraft(entry.note ?? "");
                setEditing(true);
              }}
              className="cursor-pointer text-[12px] font-semibold text-accent transition-colors hover:text-accent-deep"
            >
              {entry.note ? "Edit note" : "Add a note"}
            </button>
          ) : null}
          <button
            type="button"
            data-testid="notebook-delete"
            onClick={() => (confirming ? remove.mutate() : setConfirming(true))}
            onBlur={() => setConfirming(false)}
            disabled={remove.isPending}
            className={`cursor-pointer text-[12px] font-semibold transition-colors ${
              confirming ? "text-accent-deep" : "text-ink-faint hover:text-accent"
            }`}
          >
            {remove.isPending ? "Removing…" : confirming ? "Really remove?" : "Remove"}
          </button>
        </div>
      </div>
    </li>
  );
}

function AddWordForm() {
  const queryClient = useQueryClient();
  const [text, setText] = useState("");
  const [gloss, setGloss] = useState("");
  const [note, setNote] = useState("");

  const add = useMutation({
    mutationFn: () =>
      addNotebookEntry({
        text: text.trim(),
        gloss: gloss.trim() || undefined,
        note: note.trim() || undefined,
      }),
    onSuccess: (entry) => {
      queryClient.setQueryData<NotebookEntry[]>(NOTEBOOK_KEY, (prev) =>
        withEntry(prev, entry),
      );
      setText("");
      setGloss("");
      setNote("");
    },
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!text.trim() || add.isPending) return;
    add.mutate();
  };

  return (
    <Card testid="notebook-add-form">
      <CardLabel>Add a word</CardLabel>
      <form onSubmit={submit} className="mt-3.5 grid gap-2.5">
        <div className="grid gap-2.5 sm:grid-cols-2">
          <input
            data-testid="notebook-add-text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            maxLength={500}
            placeholder="Ijambo — the word or phrase"
            aria-label="Word or phrase (Kinyarwanda)"
            className={`${inputCls} ky text-[15px]`}
          />
          <input
            data-testid="notebook-add-gloss"
            value={gloss}
            onChange={(e) => setGloss(e.target.value)}
            maxLength={500}
            placeholder="What it means"
            aria-label="Meaning"
            className={inputCls}
          />
        </div>
        <input
          data-testid="notebook-add-note"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          maxLength={2000}
          placeholder="A note to your future self — where you heard it, how to remember it"
          aria-label="Personal note"
          className={inputCls}
        />
        {add.isError ? (
          <ErrorNote message="That didn't save — try again." testid="notebook-add-error" />
        ) : null}
        <div>
          <button
            type="submit"
            data-testid="notebook-add"
            disabled={!text.trim() || add.isPending}
            className={btnPrimary}
          >
            {add.isPending ? "Keeping…" : "Keep this word"}
          </button>
        </div>
      </form>
    </Card>
  );
}

export default function NotebookPage() {
  const notebook = useNotebook({ refetchOnMount: true });
  const entries = notebook.data ?? [];

  return (
    <div className="grid gap-3.5">
      <div className="mb-2">
        <Kicker>Ikaye · Notebook</Kicker>
        <PageTitle>Words you chose to keep.</PageTitle>
        <Lead>
          Every word you save from a lesson, a review or a practice lands here —
          with your own note on why it mattered.
        </Lead>
      </div>

      <AddWordForm />

      {notebook.isPending ? (
        <LoadingNote label="Opening your notebook…" />
      ) : notebook.isError ? (
        <ErrorNote message="Your notebook couldn't load. Refresh to try again." />
      ) : entries.length === 0 ? (
        <Card testid="notebook-empty" className="text-center">
          <p className="ky text-xl font-semibold">Nta jambo urabika.</p>
          <p className="mx-auto mt-2 max-w-[420px] text-sm text-ink-soft">
            Nothing kept yet — tap the bookmark on any sentence in a lesson,
            review or pronunciation drill, or add your first word above.
            Buhoro buhoro ni rwo rugendo.
          </p>
        </Card>
      ) : (
        <Card testid="notebook-list">
          <CardLabel>
            {entries.length} {entries.length === 1 ? "word" : "words"} kept
          </CardLabel>
          <ul className="mt-2">
            {entries.map((entry) => (
              <EntryRow key={entry.id} entry={entry} />
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
