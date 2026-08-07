"use client";

import { use, useCallback, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getScenarios } from "@/lib/api/endpoints";
import { conversationWsUrl } from "@/lib/api/client";
import { Card, CardLabel, ErrorNote, Kicker, Lead, LoadingNote, PageTitle } from "@/components/ui";
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
      className="mt-1 block cursor-pointer text-left text-xs text-ink-soft underline decoration-dotted underline-offset-2"
    >
      {open ? gloss : "gloss"}
    </button>
  );
}

/** Small play button for a partner message that carries audio. */
function MessageAudio({ url }: { url: string }) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    return () => {
      audioRef.current?.pause();
      audioRef.current = null;
    };
  }, []);

  const toggle = () => {
    if (playing) {
      audioRef.current?.pause();
      setPlaying(false);
      return;
    }
    if (!audioRef.current) {
      const audio = new Audio(url);
      audio.addEventListener("ended", () => setPlaying(false));
      audio.addEventListener("error", () => setPlaying(false));
      audioRef.current = audio;
    }
    void audioRef.current.play().catch(() => setPlaying(false));
    setPlaying(true);
  };

  return (
    <button
      type="button"
      onClick={toggle}
      data-testid="message-audio"
      aria-label={playing ? "Pause message audio" : "Play message audio"}
      className={`mt-1.5 inline-flex h-6 w-6 cursor-pointer items-center justify-center rounded-full border border-accent transition-colors ${
        playing ? "bg-accent text-on-accent" : "bg-transparent text-accent hover:bg-accent-soft"
      }`}
    >
      {playing ? (
        <svg viewBox="0 0 16 16" className="h-2 w-2 fill-current" aria-hidden>
          <rect x="3" y="3" width="10" height="10" rx="1" />
        </svg>
      ) : (
        <svg viewBox="0 0 16 16" className="ml-px h-2 w-2 fill-current" aria-hidden>
          <path d="M4 2.5v11a.6.6 0 0 0 .92.5l8.4-5.5a.6.6 0 0 0 0-1L4.92 2a.6.6 0 0 0-.92.5Z" />
        </svg>
      )}
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
  // Auto-play bookkeeping: highest entry id already auto-played, so a
  // re-render (or an older message) never replays audio in a loop.
  const autoPlayedRef = useRef(0);
  const autoAudioRef = useRef<HTMLAudioElement | null>(null);

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

  // Auto-play the newest partner message's audio exactly once (backend may
  // start sending audio_url on partner frames — optional, so guard hard).
  useEffect(() => {
    const newest = [...entries]
      .reverse()
      .find((e) => e.role === "partner" && typeof e.audioUrl === "string" && e.audioUrl);
    if (!newest || newest.id <= autoPlayedRef.current) return;
    autoPlayedRef.current = newest.id;
    try {
      autoAudioRef.current?.pause();
      const audio = new Audio(newest.audioUrl as string);
      autoAudioRef.current = audio;
      void audio.play().catch(() => {});
    } catch {
      // Autoplay is best-effort; the manual button remains.
    }
  }, [entries]);

  useEffect(() => {
    return () => {
      autoAudioRef.current?.pause();
      autoAudioRef.current = null;
    };
  }, []);

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
    <div className="grid gap-3">
      <Card testid="chat" className="flex min-h-[320px] flex-col">
        <div className="grid flex-1 content-start gap-3.5" data-testid="chat-messages">
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
                className="max-w-[78%] justify-self-center rounded-xl border border-green-line bg-green-soft px-3.5 py-3"
              >
                <p className="text-[10.5px] font-bold tracking-[0.12em] text-green uppercase">
                  Coach · {entry.coachTitle}
                </p>
                <p className="mt-[5px] text-[13px] leading-[1.55] text-green-deep">{entry.text}</p>
              </div>
            ) : (
              <div
                key={entry.id}
                data-testid={entry.role === "user" ? "user-message" : "partner-message"}
                className={
                  entry.role === "user"
                    ? "max-w-[78%] justify-self-end rounded-[14px] rounded-br-[4px] bg-bark px-4 py-3 text-paper"
                    : "max-w-[78%] justify-self-start rounded-[14px] rounded-bl-[4px] border border-line bg-cream px-4 py-3"
                }
              >
                <p className="ky text-[16.5px] leading-[1.45]">{entry.text}</p>
                {entry.role === "partner" && entry.gloss ? <GlossToggle gloss={entry.gloss} /> : null}
                {entry.role === "partner" && entry.audioUrl ? (
                  <MessageAudio url={entry.audioUrl} />
                ) : null}
              </div>
            ),
          )}
          <div ref={endRef} />
        </div>

        <div className="mt-5 border-t border-line pt-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-ink-soft">Stuck? Try:</span>
            {HINTS.map((h) => (
              <button
                key={h.ky}
                type="button"
                data-testid="hint-chip"
                title={h.en}
                onClick={() => setDraft(h.ky)}
                className="ky cursor-pointer rounded-full border border-line bg-cream px-3 py-1.5 text-[13px] transition-colors hover:border-accent hover:text-accent"
              >
                {h.ky}
              </button>
            ))}
          </div>
          <form
            className="mt-3 flex items-center gap-2.5"
            onSubmit={(e) => {
              e.preventDefault();
              sendText(draft);
            }}
          >
            <button
              type="button"
              onClick={toggleMic}
              data-testid="mic-button"
              aria-pressed={recording}
              aria-label={recording ? "Stop recording" : "Hold the mic and answer out loud"}
              className={`flex h-11 w-11 shrink-0 cursor-pointer items-center justify-center rounded-full border-[1.5px] transition-colors ${
                recording
                  ? "border-accent bg-accent"
                  : "border-accent bg-accent-soft hover:bg-[#F3D9C6]"
              }`}
            >
              <span
                aria-hidden
                className={`inline-block h-[11px] w-[11px] rounded-full ${
                  recording ? "bg-on-accent" : "bg-accent"
                }`}
              />
            </button>
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Andika mu Kinyarwanda… (type in Kinyarwanda)"
              data-testid="chat-input"
              className="min-w-0 flex-1 rounded-btn border border-line-strong bg-card px-4 py-3 text-[15px] outline-none focus:border-accent"
            />
            <button
              type="submit"
              disabled={!connected || !draft.trim()}
              data-testid="chat-send"
              className="shrink-0 cursor-pointer rounded-btn bg-accent px-5 py-3 text-sm font-semibold text-on-accent transition-colors hover:bg-accent-hover disabled:cursor-default disabled:opacity-50"
            >
              Send
            </button>
          </form>
          <p className="mt-2 ml-[54px] text-xs text-ink-faint">
            Or hold the mic and answer out loud — {scenario.persona.name.split(" ")[0]} hears your
            accent, not a transcript.
          </p>
        </div>
      </Card>

      <Card testid="scenario-goals">
        <CardLabel>Goals</CardLabel>
        <ul className="mt-3 grid gap-2">
          {scenario.goals.map((goal) => {
            const met = goalsMet.includes(goal);
            return (
              <li key={goal} className="flex items-center gap-2.5 text-sm" data-testid="goal">
                <span className={met ? "font-bold text-green" : "text-ink-faint"} aria-hidden>
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
    <div className="grid gap-3">
      <div className="mb-1">
        <Kicker>Practice · Conversation</Kicker>
        <PageTitle>{scenario.title}</PageTitle>
        <Lead>{scenario.setting}</Lead>
      </div>

      <Card testid="persona-card" className="px-[18px] py-4 sm:px-[18px] sm:py-4">
        <div className="flex flex-wrap items-center gap-3.5">
          <span className="ky flex h-11 w-11 flex-none items-center justify-center rounded-full bg-accent text-[19px] font-bold text-on-accent">
            {initial}
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-[15px] font-semibold">
              {scenario.persona.name} · {scenario.persona.role}
            </p>
            {scenario.persona.description ? (
              <p className="text-[12.5px] text-ink-soft">{scenario.persona.description}</p>
            ) : null}
          </div>
          <p className="flex-none text-right font-mono text-[10.5px] leading-[1.6] text-green uppercase">
            ● Live voice
            <br />
            Kigali
          </p>
        </div>
      </Card>

      {scenario.umuco_tip ? (
        <p
          className="rounded-btn border border-amber-line bg-amber-soft px-4 py-2.5 text-[13px] text-amber-deep"
          data-testid="umuco-tip"
        >
          <span className="font-bold text-amber-text">Umuco:</span> {scenario.umuco_tip}
        </p>
      ) : null}

      <ConversationChat scenario={scenario} />
    </div>
  );
}
