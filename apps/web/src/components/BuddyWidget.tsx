"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  BUDDY_NAME,
  BUDDY_OPENERS,
  BUDDY_TAGLINE,
  INPUT_MAX,
  autoplayCandidate,
  clampInput,
  clipState,
  playableClip,
  safeAppHref,
  type BuddyAction,
  type BuddyMessage,
} from "@/lib/buddy/state";
import {
  closeBuddy,
  hydrateBuddy,
  openBuddy,
  sendBuddyMessage,
  setBuddySound,
  useBuddy,
} from "@/lib/buddy/store";
import { isPlaying, playExclusive, stopPlayback } from "@/lib/audio/player";
import { playbackRate } from "@/lib/audio/rate";
import { useSlowAudio } from "@/lib/audio/rate-store";

/**
 * Mwarimu — the floating study buddy. Mounted once inside <AppShell>, so it
 * rides along across route changes and never appears on the unauthenticated
 * pages (/login, /register, …), which live outside the (app) group.
 *
 * The conversation itself lives in the module store; this file is presentation
 * plus the focus/keyboard contract (Escape closes, focus trapped while open,
 * focus restored to the FAB on close) and the voice: every buddy turn that
 * ordered a clip carries a play control, and the newest one speaks by itself
 * while the speaker toggle is on.
 */

const FOCUSABLE =
  'button:not([disabled]), textarea:not([disabled]), input:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])';

/** Identity on the shared audio channel — closing the panel stops only ours. */
const AUDIO_OWNER = { widget: "buddy" };

/** The sauti mark tucked inside a speech bubble — friendly, not a robot. */
function BuddyMark() {
  return (
    <svg width="27" height="27" viewBox="0 0 24 24" aria-hidden>
      <path
        d="M7 3.2h10A4.8 4.8 0 0 1 21.8 8v3.6a4.8 4.8 0 0 1-4.8 4.8h-5.2l-4.4 3.2a.6.6 0 0 1-1-.5v-2.7H7a4.8 4.8 0 0 1-4.8-4.8V8A4.8 4.8 0 0 1 7 3.2Z"
        fill="currentColor"
      />
      <path d="M6.4 13 L9.6 6.8 L12.8 13 Z" fill="#C2551A" />
      <path d="M12.8 13 L16 6.8 L19.2 13 Z" fill="#D99A2B" />
    </svg>
  );
}

function TypingDots() {
  return (
    <div
      data-testid="buddy-typing"
      className="flex w-fit items-center gap-1 rounded-[14px] rounded-bl-[4px] border border-line bg-cream px-3.5 py-3"
      aria-label={`${BUDDY_NAME} is thinking`}
    >
      {[0, 0.25, 0.5].map((delay) => (
        <span
          key={delay}
          aria-hidden
          className="animate-rhythm inline-block h-1.5 w-1.5 rounded-full bg-ink-faint"
          style={{ animationDelay: `${delay}s` }}
        />
      ))}
    </div>
  );
}

/** Speaker cone, shared by the header toggle and the waiting play control. */
function SpeakerGlyph({ muted = false, className = "" }: { muted?: boolean; className?: string }) {
  return (
    <svg viewBox="0 0 16 16" className={className} fill="none" aria-hidden>
      <path d="M8.6 2.6 4.9 5.5H2.6v5h2.3l3.7 2.9z" fill="currentColor" />
      {muted ? (
        <path
          d="M11.2 6.1 14.4 9.9M14.4 6.1 11.2 9.9"
          stroke="currentColor"
          strokeWidth="1.4"
          strokeLinecap="round"
        />
      ) : (
        <>
          <path
            d="M11.1 6.1a2.6 2.6 0 0 1 0 3.8"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="round"
          />
          <path
            d="M13 4.4a5 5 0 0 1 0 7.2"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="round"
          />
        </>
      )}
    </svg>
  );
}

/**
 * Play control for one buddy turn — the whole point of the exercise: the
 * learner can hear the Kinyarwanda, not just read it.
 *
 * pending  the server promised a clip and synthesis is still running. Dimmed
 *          and not clickable, with the same slow breathing as the typing dots
 *          — a waiting affordance, not a spinner that looks stuck.
 * ready    tap to play.
 * playing  tap to stop.
 */
function ClipButton({
  state,
  onToggle,
}: {
  state: "pending" | "ready" | "playing";
  onToggle: () => void;
}) {
  const pending = state === "pending";
  const playing = state === "playing";
  const label = pending
    ? `${BUDDY_NAME} is finding his voice…`
    : playing
      ? "Stop"
      : `Hear ${BUDDY_NAME} say this`;

  return (
    <button
      type="button"
      data-testid="buddy-play"
      data-state={state}
      disabled={pending}
      onClick={onToggle}
      aria-label={label}
      title={label}
      className={`inline-flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-full border-[1.5px] transition-colors ${
        pending
          ? "animate-rhythm cursor-default border-line-strong bg-transparent text-ink-faint"
          : playing
            ? "cursor-pointer border-accent bg-accent text-on-accent"
            : "cursor-pointer border-accent bg-transparent text-accent hover:bg-accent-soft"
      }`}
    >
      {pending ? (
        <SpeakerGlyph className="h-3 w-3" />
      ) : playing ? (
        <svg viewBox="0 0 16 16" className="h-[9px] w-[9px] fill-current" aria-hidden>
          <rect x="3" y="3" width="10" height="10" rx="1" />
        </svg>
      ) : (
        <svg viewBox="0 0 16 16" className="ml-0.5 h-[9px] w-[9px] fill-current" aria-hidden>
          <path d="M4 2.5v11a.6.6 0 0 0 .92.5l8.4-5.5a.6.6 0 0 0 0-1L4.92 2a.6.6 0 0 0-.92.5Z" />
        </svg>
      )}
    </button>
  );
}

function ActionChip({ action, onGo }: { action: BuddyAction; onGo: (href: string) => void }) {
  const href = safeAppHref(action.href);
  if (!href) return null;
  return (
    <button
      type="button"
      data-testid="buddy-action"
      data-href={href}
      onClick={() => onGo(href)}
      className="cursor-pointer rounded-full border border-accent-soft-line bg-accent-soft px-3 py-1.5 text-[12.5px] font-semibold text-accent-deep transition-colors hover:border-accent hover:bg-[#f3d9c6]"
    >
      {action.label} →
    </button>
  );
}

function Bubble({
  message,
  onGo,
  playing,
  onToggleClip,
}: {
  message: BuddyMessage;
  onGo: (href: string) => void;
  playing: boolean;
  onToggleClip: (message: BuddyMessage) => void;
}) {
  const learner = message.role === "learner";
  const clip = clipState(message);
  const bubble = learner
    ? "justify-self-end rounded-[14px] rounded-br-[4px] bg-bark px-3.5 py-2.5 text-paper"
    : message.tone === "error"
      ? "justify-self-start rounded-[14px] rounded-bl-[4px] border border-amber-line bg-amber-soft px-3.5 py-2.5 text-amber-deep"
      : "justify-self-start rounded-[14px] rounded-bl-[4px] border border-line bg-cream px-3.5 py-2.5";

  return (
    <div className={`grid max-w-[86%] gap-1.5 ${learner ? "justify-self-end" : ""}`}>
      {message.text ? (
        <div data-testid="buddy-message" data-role={message.role} className={bubble}>
          {/* A gloss means the line is Kinyarwanda: give it the serif face. */}
          <p
            className={
              message.gloss
                ? "ky text-[15.5px] leading-[1.45]"
                : "text-[13.5px] leading-[1.55] whitespace-pre-wrap"
            }
          >
            {message.text}
          </p>
          {message.gloss ? (
            <p
              data-testid="buddy-gloss"
              className={`mt-1 text-[12px] ${learner ? "text-bark-mute" : "text-ink-soft"}`}
            >
              {message.gloss}
            </p>
          ) : null}
        </div>
      ) : null}
      {clip === "none" ? null : (
        <ClipButton
          state={playing && clip === "ready" ? "playing" : clip}
          onToggle={() => onToggleClip(message)}
        />
      )}
      {message.actions?.length ? (
        <div className="flex flex-wrap gap-1.5">
          {message.actions.map((action) => (
            <ActionChip key={action.href} action={action} onGo={onGo} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function BuddyWidget() {
  const router = useRouter();
  const { messages, awaiting, open, soundOn } = useBuddy();
  // Mwarimu speaks Kinyarwanda too, so he follows the app-wide slow
  // preference. Held in a ref so flipping it can't re-fire the autoplay
  // effect and make an old turn speak again.
  const alwaysSlow = useSlowAudio();
  const alwaysSlowRef = useRef(alwaysSlow);
  useEffect(() => {
    alwaysSlowRef.current = alwaysSlow;
  }, [alwaysSlow]);
  const [draft, setDraft] = useState("");
  const [playingId, setPlayingId] = useState<number | null>(null);
  const fabRef = useRef<HTMLButtonElement | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);
  const wasOpen = useRef(false);
  /**
   * Turns whose clip we have already played or offered to the browser. A
   * message leaves this set never — one autoplay per reply, even if it comes
   * back around through a re-render, a reopen or a blocked play().
   */
  const heardRef = useRef<Set<number>>(new Set());
  /** Bumped on every start/stop so a late play() promise can't resurrect. */
  const turnRef = useRef(0);

  useEffect(() => {
    hydrateBuddy();
  }, []);

  const stopClip = useCallback(() => {
    turnRef.current += 1;
    stopPlayback(AUDIO_OWNER);
    setPlayingId(null);
  }, []);

  /**
   * Start a clip. `auto` marks the hands-free path: the button state only
   * follows a *confirmed* start there, because a blocked autoplay must leave
   * the control sitting in its plain "ready" state, not flicker as if it had
   * played. A tap is a gesture the browser honours, so it lights up at once.
   */
  const playClip = useCallback((message: BuddyMessage, auto = false) => {
    const url = playableClip(message);
    if (!url) return;
    turnRef.current += 1;
    const turn = turnRef.current;
    heardRef.current.add(message.id);
    if (!auto) setPlayingId(message.id);
    void playExclusive(url, {
      owner: AUDIO_OWNER,
      rate: playbackRate({ alwaysSlow: alwaysSlowRef.current }),
      onStop: () => {
        if (turnRef.current === turn) setPlayingId(null);
      },
    }).then((started) => {
      // Blocked autoplay, a dead URL, or someone stopped us while play() was
      // still settling: fall back to the plain ready button, quietly.
      if (turnRef.current !== turn) return;
      setPlayingId(started && isPlaying(AUDIO_OWNER) ? message.id : null);
    });
  }, []);

  const toggleClip = useCallback(
    (message: BuddyMessage) => {
      if (playingId === message.id) stopClip();
      else playClip(message);
    },
    [playingId, playClip, stopClip],
  );

  // Hands-free: the newest reply speaks as soon as its clip lands. Older
  // turns never do, a turn never speaks twice, and a shut panel stays quiet.
  useEffect(() => {
    const target = autoplayCandidate(messages, {
      soundOn,
      open,
      heard: heardRef.current,
    });
    if (target) playClip(target, true);
  }, [messages, soundOn, open, playClip]);

  // Silence on close and on mute. Stopping the channel fires the clip's own
  // onStop, which is what clears the button — no state is set from here.
  useEffect(() => {
    if (!open || !soundOn) stopPlayback(AUDIO_OWNER);
  }, [open, soundOn]);

  useEffect(() => () => stopPlayback(AUDIO_OWNER), []);

  // Focus in on open, back to the FAB on close.
  useEffect(() => {
    if (open) {
      wasOpen.current = true;
      inputRef.current?.focus();
    } else if (wasOpen.current) {
      wasOpen.current = false;
      fabRef.current?.focus();
    }
  }, [open]);

  useEffect(() => {
    if (open) endRef.current?.scrollIntoView({ block: "end" });
  }, [open, messages, awaiting]);

  // Escape closes from anywhere while the panel is up — focus may sit on a
  // control that has just been disabled (the send button after a send), so a
  // panel-scoped handler alone would miss the key.
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeBuddy();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open]);

  const go = useCallback(
    (href: string) => {
      // Leaving on a chip: the panel goes away, so the voice goes with it.
      stopClip();
      closeBuddy();
      router.push(href);
    },
    [router, stopClip],
  );

  const submit = () => {
    if (!draft.trim()) return;
    sendBuddyMessage(draft);
    setDraft("");
    // The send button disables itself on an empty draft; keep the caret where
    // the learner is about to type instead of dropping focus to <body>.
    inputRef.current?.focus();
  };

  /** Tab is trapped inside the panel while it's open (Escape lives on window). */
  const onPanelKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "Tab" || !panelRef.current) return;
    const nodes = Array.from(panelRef.current.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
      (el) => el.offsetParent !== null || el === document.activeElement,
    );
    if (nodes.length === 0) return;
    const first = nodes[0];
    const last = nodes[nodes.length - 1];
    const active = document.activeElement;
    if (event.shiftKey && (active === first || !panelRef.current.contains(active))) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && active === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const remaining = INPUT_MAX - draft.length;
  const firstRun = messages.length <= 1;

  return (
    <>
      <button
        ref={fabRef}
        type="button"
        data-testid="buddy-fab"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label={open ? `Close ${BUDDY_NAME}` : `Chat with ${BUDDY_NAME}, your study buddy`}
        onClick={() => (open ? closeBuddy() : openBuddy())}
        className={`fixed right-5 bottom-5 z-40 flex h-14 w-14 cursor-pointer items-center justify-center rounded-full bg-accent text-on-accent shadow-[0_10px_28px_-8px_rgba(36,28,18,0.45)] ring-2 ring-gold/45 transition-transform hover:scale-105 hover:bg-accent-hover focus-visible:ring-4 sm:right-6 sm:bottom-6 ${
          open ? "max-sm:hidden" : ""
        }`}
      >
        <BuddyMark />
        <span
          aria-hidden
          className="animate-rhythm absolute top-1 right-1 h-2 w-2 rounded-full bg-gold"
        />
      </button>

      {open ? (
        <div
          ref={panelRef}
          role="dialog"
          aria-modal="false"
          aria-label={`${BUDDY_NAME} — study buddy`}
          data-testid="buddy-panel"
          onKeyDown={onPanelKeyDown}
          className="fixed inset-0 z-50 flex flex-col bg-card sm:inset-auto sm:right-6 sm:bottom-24 sm:h-[520px] sm:max-h-[calc(100vh-8rem)] sm:w-[380px] sm:rounded-card sm:border sm:border-line sm:shadow-[0_18px_50px_-20px_rgba(36,28,18,0.5)]"
        >
          <header className="flex items-start gap-3 rounded-t-none bg-bark px-4 py-3.5 text-paper sm:rounded-t-card">
            <span
              aria-hidden
              className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-accent text-on-accent"
            >
              <BuddyMark />
            </span>
            <div className="min-w-0 flex-1">
              <p className="ky text-[16px] leading-tight font-semibold text-paper">{BUDDY_NAME}</p>
              <p className="mt-0.5 text-[11.5px] leading-snug text-bark-mute">{BUDDY_TAGLINE}</p>
            </div>
            <button
              type="button"
              data-testid="buddy-sound-toggle"
              data-on={soundOn}
              aria-pressed={soundOn}
              onClick={() => setBuddySound(!soundOn)}
              aria-label={
                soundOn ? `Turn ${BUDDY_NAME}'s voice off` : `Turn ${BUDDY_NAME}'s voice on`
              }
              title={soundOn ? "Voice on — replies play themselves" : "Voice off — tap ▶ to hear"}
              className={`-mt-1 flex h-8 w-8 flex-none cursor-pointer items-center justify-center rounded-full transition-colors hover:bg-paper/10 ${
                soundOn ? "text-gold hover:text-gold" : "text-bark-soft hover:text-paper"
              }`}
            >
              <SpeakerGlyph muted={!soundOn} className="h-4 w-4" />
            </button>
            <button
              type="button"
              data-testid="buddy-close"
              onClick={() => closeBuddy()}
              aria-label={`Close ${BUDDY_NAME}`}
              className="-mt-1 -mr-1 flex h-8 w-8 flex-none cursor-pointer items-center justify-center rounded-full text-bark-soft transition-colors hover:bg-paper/10 hover:text-paper"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden>
                <path
                  d="M1 1 13 13M13 1 1 13"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                />
              </svg>
            </button>
          </header>

          <div
            className="flex-1 overflow-y-auto px-4 py-4"
            aria-live="polite"
            data-testid="buddy-messages"
          >
            <div className="grid gap-2.5">
              {messages.map((message) => (
                <Bubble
                  key={message.id}
                  message={message}
                  onGo={go}
                  playing={playingId === message.id}
                  onToggleClip={toggleClip}
                />
              ))}
              {awaiting ? <TypingDots /> : null}
              <div ref={endRef} />
            </div>
          </div>

          {firstRun ? (
            <div className="flex flex-wrap gap-1.5 border-t border-line px-4 pt-3">
              {BUDDY_OPENERS.map((opener) => (
                <button
                  key={opener}
                  type="button"
                  data-testid="buddy-opener"
                  onClick={() => {
                    setDraft(opener);
                    inputRef.current?.focus();
                  }}
                  className="cursor-pointer rounded-full border border-line-strong bg-cream px-3 py-1.5 text-[12px] text-ink-soft transition-colors hover:border-accent hover:text-accent"
                >
                  {opener}
                </button>
              ))}
            </div>
          ) : null}

          <form
            className={`flex items-end gap-2 px-4 pt-3 pb-4 ${firstRun ? "" : "border-t border-line"}`}
            onSubmit={(event) => {
              event.preventDefault();
              submit();
            }}
          >
            <div className="min-w-0 flex-1">
              <textarea
                ref={inputRef}
                rows={1}
                value={draft}
                maxLength={INPUT_MAX}
                data-testid="buddy-input"
                aria-label={`Message ${BUDDY_NAME}`}
                placeholder="Ask me anything you've learned…"
                onChange={(event) => setDraft(clampInput(event.target.value))}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    submit();
                  }
                }}
                className="max-h-28 w-full resize-none rounded-btn border border-line-strong bg-card px-3.5 py-2.5 text-[13.5px] outline-none focus:border-accent"
              />
              {remaining <= 80 ? (
                <p className="mt-1 text-right text-[11px] text-ink-faint" data-testid="buddy-count">
                  {remaining} left
                </p>
              ) : null}
            </div>
            <button
              type="submit"
              data-testid="buddy-send"
              disabled={!draft.trim()}
              className="flex h-[42px] w-[42px] flex-none cursor-pointer items-center justify-center rounded-btn bg-accent text-on-accent transition-colors hover:bg-accent-hover disabled:cursor-default disabled:opacity-45"
              aria-label="Send"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden>
                <path d="M1.4 14.6 15 8 1.4 1.4l2.2 5.4L10 8l-6.4 1.2z" fill="currentColor" />
              </svg>
            </button>
          </form>
        </div>
      ) : null}
    </>
  );
}
