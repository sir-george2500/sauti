"use client";

import { use, useCallback, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getScenarios } from "@/lib/api/endpoints";
import { conversationWsUrl } from "@/lib/api/client";
import { Card, ErrorNote, Kicker, LoadingNote, PageTitle } from "@/components/ui";
import type { ConversationServerMessage, Scenario } from "@/lib/api/types";

interface ChatEntry {
  id: number;
  role: "user" | "partner" | "coach";
  text: string;
  gloss?: string | null;
  coachTitle?: string;
  coachKind?: "fix" | "praise" | "culture";
  audioUrl?: string | null;
}

const HINTS = [
  { ky: "Muraho! Amakuru?", en: "Hello! How are you?" },
  { ky: "Ni angahe?", en: "How much is it?" },
  { ky: "Gabanya gato…", en: "Lower it a little…" },
  { ky: "Ongera uvuge buhoro.", en: "Say it again, slowly." },
] as const;

function GlossToggle({ gloss }: { gloss: string }) {
  const [open, setOpen] = useState(false);
  return (
    <button
      type="button"
      data-testid="gloss-toggle"
      onClick={() => setOpen((v) => !v)}
      className="mt-1 block text-left text-xs text-ink-soft underline decoration-dotted underline-offset-2"
    >
      {open ? gloss : "gloss"}
    </button>
  );
}

function ConversationChat({ scenario }: { scenario: Scenario }) {
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [goalsMet, setGoalsMet] = useState<string[]>([]);
  const [draft, setDraft] = useState("");
  const [connected, setConnected] = useState(false);
  const [recording, setRecording] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const nextId = useRef(1);
  const endRef = useRef<HTMLDivElement | null>(null);

  const append = useCallback((entry: Omit<ChatEntry, "id">) => {
    setEntries((prev) => [...prev, { ...entry, id: nextId.current++ }]);
  }, []);

  useEffect(() => {
    const ws = new WebSocket(conversationWsUrl(scenario.id));
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (event) => {
      let msg: ConversationServerMessage;
      try {
        msg = JSON.parse(event.data as string) as ConversationServerMessage;
      } catch {
        return;
      }
      if (msg.type === "partner") {
        append({ role: "partner", text: msg.text, gloss: msg.gloss, audioUrl: msg.audio_url });
      } else if (msg.type === "coach") {
        append({
          role: "coach",
          text: msg.coach?.body ?? msg.text,
          coachTitle: msg.coach?.title ?? "Coach",
          coachKind: msg.coach?.kind ?? "fix",
        });
      } else if (msg.type === "goal") {
        setGoalsMet((prev) => (prev.includes(msg.text) ? prev : [...prev, msg.text]));
      } else if (msg.type === "error") {
        append({ role: "coach", text: msg.text, coachTitle: "Hiccup", coachKind: "fix" });
      }
    };
    return () => {
      wsRef.current = null;
      ws.close();
    };
  }, [scenario.id, append]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [entries]);

  const sendText = (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || wsRef.current?.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ text: trimmed }));
    append({ role: "user", text: trimmed });
    setDraft("");
  };

  // Mic is a stub for MVP: it really records, but sends a placeholder
  // audio_ref over the socket (speech models aren't wired yet — SPEC §2).
  const toggleMic = async () => {
    if (recording) {
      recorderRef.current?.stop();
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      recorderRef.current = recorder;
      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        setRecording(false);
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ audio_ref: "stub:mic-take" }));
          append({ role: "user", text: "🎙 (spoken answer)" });
        }
      };
      recorder.start();
      setRecording(true);
    } catch {
      append({
        role: "coach",
        text: "We couldn't reach your microphone — type your answer instead.",
        coachTitle: "Mic",
        coachKind: "fix",
      });
    }
  };

  return (
    <div className="grid gap-6">
      <Card testid="chat" className="flex min-h-[320px] flex-col">
        <div className="grid flex-1 content-start gap-3" data-testid="chat-messages">
          {entries.length === 0 ? (
            <p className="py-8 text-center text-sm text-ink-soft">
              {connected
                ? `${scenario.persona.name.split(" ")[0]} is waiting — greet first.`
                : "Connecting to the market…"}
            </p>
          ) : null}
          {entries.map((entry) =>
            entry.role === "coach" ? (
              <div
                key={entry.id}
                data-testid="coach-note"
                className="rounded-xl border border-accent/25 bg-accent-soft px-4 py-3"
              >
                <p className="text-[10px] font-semibold tracking-[0.16em] text-accent-deep uppercase">
                  Coach · {entry.coachTitle}
                </p>
                <p className="mt-1 text-sm leading-relaxed">{entry.text}</p>
              </div>
            ) : (
              <div
                key={entry.id}
                data-testid={entry.role === "user" ? "user-message" : "partner-message"}
                className={
                  entry.role === "user"
                    ? "justify-self-end rounded-2xl rounded-br-sm bg-ink px-4 py-2.5 text-paper"
                    : "max-w-[85%] justify-self-start rounded-2xl rounded-bl-sm border border-line bg-paper px-4 py-2.5"
                }
              >
                <p className="ky">{entry.text}</p>
                {entry.role === "partner" && entry.gloss ? <GlossToggle gloss={entry.gloss} /> : null}
              </div>
            ),
          )}
          <div ref={endRef} />
        </div>

        <div className="mt-5 border-t border-line pt-4">
          <p className="text-xs text-ink-soft">Stuck? Try:</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {HINTS.map((h) => (
              <button
                key={h.ky}
                type="button"
                data-testid="hint-chip"
                title={h.en}
                onClick={() => setDraft(h.ky)}
                className="ky rounded-full border border-line bg-cream px-3 py-1.5 text-sm transition-colors hover:border-accent"
              >
                {h.ky}
              </button>
            ))}
          </div>
          <form
            className="mt-3 flex items-center gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              sendText(draft);
            }}
          >
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Andika hano — write here…"
              data-testid="chat-input"
              className="ky min-w-0 flex-1 rounded-full border border-line bg-card px-4 py-2.5 outline-none focus:border-accent"
            />
            <button
              type="button"
              onClick={toggleMic}
              data-testid="mic-button"
              aria-pressed={recording}
              aria-label={recording ? "Stop recording" : "Hold the mic and answer out loud"}
              className={`h-11 w-11 shrink-0 rounded-full border transition-colors ${
                recording
                  ? "border-accent bg-accent text-paper"
                  : "border-line bg-cream text-accent-deep hover:border-accent"
              }`}
            >
              <span aria-hidden>{recording ? "■" : "🎙"}</span>
            </button>
            <button
              type="submit"
              disabled={!connected || !draft.trim()}
              data-testid="chat-send"
              className="shrink-0 rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-paper transition-colors hover:bg-accent-deep disabled:opacity-50"
            >
              Send
            </button>
          </form>
          <p className="mt-2 text-xs text-ink-soft">
            Or hold the mic and answer out loud — {scenario.persona.name.split(" ")[0]} hears your
            accent, not a transcript.
          </p>
        </div>
      </Card>

      <Card testid="scenario-goals">
        <Kicker>Goals</Kicker>
        <ul className="mt-3 grid gap-2">
          {scenario.goals.map((goal) => {
            const met = goalsMet.includes(goal);
            return (
              <li key={goal} className="flex items-center gap-2 text-sm" data-testid="goal">
                <span className={met ? "text-accent-deep" : "text-ink-soft"} aria-hidden>
                  {met ? "✓" : "○"}
                </span>
                <span className={met ? "" : "text-ink-soft"}>{goal}</span>
              </li>
            );
          })}
        </ul>
      </Card>
    </div>
  );
}

export default function ConversationPage({
  params,
}: {
  params: Promise<{ scenarioId: string }>;
}) {
  const { scenarioId } = use(params);
  const scenarios = useQuery({ queryKey: ["scenarios"], queryFn: getScenarios });

  if (scenarios.isPending) return <LoadingNote label="Setting up the stall…" />;
  if (scenarios.isError) {
    return <ErrorNote message="Scenarios couldn't load. Refresh to try again." />;
  }

  const scenario = scenarios.data.find((s) => s.id === scenarioId);
  if (!scenario) return <ErrorNote message="That scenario isn't available at your level yet." />;

  const initial = scenario.persona.name.charAt(0).toUpperCase();

  return (
    <div className="grid gap-6">
      <div>
        <Kicker>Practice · Conversation</Kicker>
        <PageTitle>{scenario.title}</PageTitle>
        <p className="mt-2 max-w-lg text-ink-soft">{scenario.setting}</p>
      </div>

      <Card testid="persona-card">
        <div className="flex flex-wrap items-center gap-4">
          <span className="ky flex h-12 w-12 items-center justify-center rounded-full bg-ink text-xl text-paper">
            {initial}
          </span>
          <div className="min-w-0 flex-1">
            <p className="font-medium">
              {scenario.persona.name} · {scenario.persona.role}
            </p>
            {scenario.persona.description ? (
              <p className="text-sm text-ink-soft">{scenario.persona.description}</p>
            ) : null}
          </div>
          <span className="inline-flex items-center gap-2 rounded-full border border-line bg-cream px-3 py-1 text-[10px] font-semibold tracking-[0.16em] uppercase">
            <span className="text-accent">●</span> Live voice
            <span className="font-normal text-ink-soft">Kigali</span>
          </span>
        </div>
        {scenario.umuco_tip ? (
          <p className="mt-4 rounded-xl bg-accent-soft px-4 py-3 text-sm" data-testid="umuco-tip">
            <span className="font-semibold text-accent-deep">Umuco:</span> {scenario.umuco_tip}
          </p>
        ) : null}
      </Card>

      <ConversationChat scenario={scenario} />
    </div>
  );
}
