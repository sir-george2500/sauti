/**
 * Mwarimu — the floating study buddy.
 *
 * This module is the pure half: frame parsing, the message reducer, the
 * same-origin href guard and the input cap. No React, no WebSocket, no
 * browser globals — so every rule here is unit-testable (`state.test.ts`).
 *
 * Wire contract (WS /api/v1/ws/buddy?token=…):
 *   client → {text}
 *   server → {type:"buddy", id?, text, gloss?}
 *          | {type:"buddy_audio", id, audio_url}
 *          | {type:"action", action:{kind:"navigate", href, label}}
 *          | {type:"error", text}
 * Everything is treated as untrusted: unknown frame types are dropped, a
 * malformed buddy frame still clears the typing indicator, an action whose
 * href isn't an in-app path is discarded outright, and a clip URL that isn't
 * http(s) or a same-origin path never reaches an <audio> element.
 *
 * Voice is a follow-up, not a promise: a buddy frame carrying an `id` says a
 * clip is being synthesized, and the matching `buddy_audio` frame lands a few
 * seconds later — or never, if the voice service is down. That silence is a
 * normal degradation (the turn stays readable), never an error.
 */

export const BUDDY_NAME = "Mwarimu";
export const BUDDY_TAGLINE = "Half teacher, half hype-man. Quiz me, or let me quiz you.";

/** Hard cap on what we'll put on the wire in one turn. */
export const INPUT_MAX = 500;

/** Openers so the first-run panel is never a blank box. */
export const BUDDY_OPENERS: readonly string[] = [
  "What did I learn today?",
  "Quiz me on my notebook words",
  "What should I do next?",
];

/** Static, zero-cost hello — an idle open must never spend an LLM call. */
export const BUDDY_GREETING =
  "Muraho! Mwarimu here — part teacher, part hype-man, and I never forget a word you've learned. What are we chewing on today?";

/** Shown when the socket won't come back; still in character, never a stack trace. */
export const BUDDY_OFFLINE =
  "Ayi — I lost the line for a second. Say it again and I'll catch it this time.";

/** Shown when a turn goes out but nothing comes back. */
export const BUDDY_SILENCE = "Mmh. I opened my mouth and nothing came out. Nudge me again?";

const ERROR_FALLBACK =
  "Aya! My brain tripped over a rock there. Try me once more — I'm tougher than I look.";

export interface BuddyAction {
  kind: "navigate";
  href: string;
  label: string;
}

export interface BuddyMessage {
  id: number;
  role: "learner" | "buddy";
  text: string;
  /** English gloss; its presence means `text` is Kinyarwanda (rendered in `ky`). */
  gloss?: string;
  /** Error frames keep the conversation usable but wear a warmer skin. */
  tone?: "error";
  /** Guidance chips, attached to the buddy turn they belong to. */
  actions?: BuddyAction[];
  /**
   * Server clip id. Its presence means a voice clip was promised for this
   * turn — the play control waits on it (`pending`) until `audioUrl` lands.
   */
  audioId?: string;
  /** Playable clip URL, set by the follow-up `buddy_audio` frame. */
  audioUrl?: string;
}

export interface BuddyState {
  messages: BuddyMessage[];
  /** True between a learner send and the next server frame (typing indicator). */
  awaiting: boolean;
  nextId: number;
}

export const initialBuddyState: BuddyState = {
  messages: [],
  awaiting: false,
  nextId: 1,
};

/** At most this many chips hang off one buddy turn. */
const MAX_ACTIONS = 4;

// ---------------------------------------------------------------------------
// Guards
// ---------------------------------------------------------------------------

/**
 * Open-redirect guard for action hrefs — the same rule the login `?next=`
 * param uses, hardened a little: only in-app absolute paths are followed.
 * Accepts "/vocab", "/lesson/x?y=1#z"; rejects "//evil.com", "https://…",
 * "javascript:…", "/\evil.com" (browsers normalise `/\` to `//`), bare
 * relative paths and anything carrying control characters.
 */
export function safeAppHref(href: unknown): string | null {
  if (typeof href !== "string") return null;
  const trimmed = href.trim();
  if (!trimmed.startsWith("/")) return null;
  if (trimmed.startsWith("//") || trimmed.startsWith("/\\")) return null;
  if (/[\u0000-\u001f\u007f]/.test(trimmed)) return null;
  return trimmed;
}

/** Longest clip URL we'll hand to an <audio> element. */
const AUDIO_URL_MAX = 2048;
/** Longest server clip id we'll keep on a message. */
const CLIP_ID_MAX = 128;

/**
 * Guard for a clip URL off the wire. Only an absolute http(s) URL (the TTS
 * host / CDN) or a same-origin path is playable; `javascript:`, `data:`,
 * `blob:`, protocol-relative `//host` and anything with control characters
 * are refused, so a hostile frame can never become an <audio> src.
 */
export function safeAudioUrl(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const url = value.trim();
  if (!url || url.length > AUDIO_URL_MAX) return null;
  if (/[\u0000-\u001f\u007f]/.test(url)) return null;
  if (/^https?:\/\/[^/\\?#]+/i.test(url)) return url;
  if (url.startsWith("//") || url.startsWith("/\\")) return null;
  return url.startsWith("/") ? url : null;
}

/** Guard for the id that ties a `buddy_audio` frame back to its turn. */
export function safeClipId(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const id = value.trim();
  if (!id || id.length > CLIP_ID_MAX) return null;
  return /[\u0000-\u001f\u007f]/.test(id) ? null : id;
}

/** Trim to the wire cap. Used by the textarea and again before sending. */
export function clampInput(text: string): string {
  return text.length > INPUT_MAX ? text.slice(0, INPUT_MAX) : text;
}

/** What actually goes on the wire, or null when there's nothing to say. */
export function prepareOutgoing(text: string): string | null {
  const trimmed = clampInput(text).trim();
  return trimmed ? trimmed : null;
}

/**
 * Server error text is only shown when it reads like a sentence a buddy would
 * say. Anything that smells of a stack trace, markup or JSON is swapped for
 * our own in-character line.
 */
export function humanizeError(text: unknown): string {
  if (typeof text !== "string") return ERROR_FALLBACK;
  const line = text.trim();
  if (!line || line.length > 160) return ERROR_FALLBACK;
  if (/[\n\r\t]/.test(line)) return ERROR_FALLBACK;
  if (/traceback|exception|<[a-z/!]|[{}<>]|\w+error\b|error:|\bat .+:\d+/i.test(line)) {
    return ERROR_FALLBACK;
  }
  return line;
}

// ---------------------------------------------------------------------------
// Frame parsing
// ---------------------------------------------------------------------------

export type BuddyFrame =
  | { type: "buddy"; text: string; gloss?: string; id?: string }
  | { type: "buddy_audio"; id: string; audioUrl: string }
  | { type: "action"; action: BuddyAction }
  | { type: "error"; text: string };

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function nonEmptyString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

/**
 * Parse one server frame. Accepts the raw string off the socket or an already
 * decoded object. Unknown/garbage frames return null and are ignored.
 */
export function parseFrame(raw: unknown): BuddyFrame | null {
  let value: unknown = raw;
  if (typeof raw === "string") {
    try {
      value = JSON.parse(raw);
    } catch {
      return null;
    }
  }
  const frame = asRecord(value);
  if (!frame) return null;

  switch (frame.type) {
    case "buddy": {
      const text = nonEmptyString(frame.text);
      // A buddy frame with no words still counts as a turn: show the
      // in-character fallback rather than leaving the typing dots spinning.
      if (!text) return { type: "error", text: ERROR_FALLBACK };
      const gloss = nonEmptyString(frame.gloss);
      // An id (when the server sends one) means a clip is on its way.
      const id = safeClipId(frame.id);
      return {
        type: "buddy",
        text,
        ...(gloss ? { gloss } : {}),
        ...(id ? { id } : {}),
      };
    }
    case "buddy_audio": {
      // Both halves must be sound: an id we can match and a URL we can play.
      const id = safeClipId(frame.id);
      const audioUrl = safeAudioUrl(frame.audio_url);
      return id && audioUrl ? { type: "buddy_audio", id, audioUrl } : null;
    }
    case "action": {
      const action = asRecord(frame.action);
      if (!action || action.kind !== "navigate") return null;
      const href = safeAppHref(action.href);
      if (!href) return null;
      const label = nonEmptyString(action.label) ?? "Take me there";
      return { type: "action", action: { kind: "navigate", href, label } };
    }
    case "error":
      return { type: "error", text: humanizeError(frame.text) };
    default:
      return null;
  }
}

// ---------------------------------------------------------------------------
// Reducer
// ---------------------------------------------------------------------------

export type BuddyEvent =
  /** The learner sent a turn. */
  | { kind: "learner"; text: string }
  /** A raw frame off the socket (string or object). */
  | { kind: "frame"; frame: unknown }
  /** A client-side line from the buddy (greeting, offline note). */
  | { kind: "say"; text: string; tone?: "error" }
  | { kind: "awaiting"; value: boolean }
  | { kind: "reset" };

function append(state: BuddyState, message: Omit<BuddyMessage, "id">): BuddyState {
  return {
    ...state,
    messages: [...state.messages, { ...message, id: state.nextId }],
    nextId: state.nextId + 1,
  };
}

/** Hang an action chip off the newest buddy turn (creating one if need be). */
function attachAction(state: BuddyState, action: BuddyAction): BuddyState {
  const index = state.messages.map((m) => m.role).lastIndexOf("buddy");
  if (index === -1) return append(state, { role: "buddy", text: "", actions: [action] });
  const target = state.messages[index];
  const actions = target.actions ?? [];
  if (actions.some((a) => a.href === action.href) || actions.length >= MAX_ACTIONS) {
    return state;
  }
  const messages = state.messages.slice();
  messages[index] = { ...target, actions: [...actions, action] };
  return { ...state, messages };
}

/**
 * Hang a synthesized clip on the turn that ordered it, matched by the server's
 * id. No match (a stale id, a turn the tab never saw, a second clip for the
 * same id) → the frame is dropped and the state object is returned untouched.
 */
function attachAudio(state: BuddyState, id: string, audioUrl: string): BuddyState {
  const index = state.messages.findIndex(
    (m) => m.role === "buddy" && m.audioId === id && !m.audioUrl,
  );
  if (index === -1) return state;
  const messages = state.messages.slice();
  messages[index] = { ...messages[index], audioUrl };
  return { ...state, messages };
}

export function reduceBuddy(state: BuddyState, event: BuddyEvent): BuddyState {
  switch (event.kind) {
    case "learner": {
      const text = prepareOutgoing(event.text);
      if (!text) return state;
      return { ...append(state, { role: "learner", text }), awaiting: true };
    }
    case "say":
      return append(state, {
        role: "buddy",
        text: event.text,
        tone: event.tone,
      });
    case "awaiting":
      return state.awaiting === event.value ? state : { ...state, awaiting: event.value };
    case "reset":
      return initialBuddyState;
    case "frame": {
      const frame = parseFrame(event.frame);
      if (!frame) return state;
      if (frame.type === "action") return { ...attachAction(state, frame.action), awaiting: false };
      // A clip lands on an existing turn: no new bubble, and the typing
      // indicator is not this frame's business.
      if (frame.type === "buddy_audio") return attachAudio(state, frame.id, frame.audioUrl);
      const next =
        frame.type === "buddy"
          ? append(state, {
              role: "buddy",
              text: frame.text,
              gloss: frame.gloss,
              audioId: frame.id,
            })
          : append(state, { role: "buddy", text: frame.text, tone: "error" });
      return { ...next, awaiting: false };
    }
    default:
      return state;
  }
}

// ---------------------------------------------------------------------------
// Playback rules
// ---------------------------------------------------------------------------

/** What the play control shows for a turn. "playing" is UI-only, on top. */
export type ClipState = "none" | "pending" | "ready";

/**
 * The URL this turn can actually play, re-checked at the point of use — a
 * message can also arrive from sessionStorage, which is not the wire but is
 * still not our own memory.
 */
export function playableClip(message: BuddyMessage | null | undefined): string | null {
  if (!message || message.role !== "buddy") return null;
  return safeAudioUrl(message.audioUrl);
}

/**
 * `pending` while a promised clip is still being synthesized, `ready` once a
 * playable URL has landed, `none` when the turn was never going to speak (the
 * static greeting, an offline note, a server with no voice service). A clip
 * that never arrives simply stays pending — silence is not an error.
 */
export function clipState(message: BuddyMessage): ClipState {
  if (message.role !== "buddy") return "none";
  if (playableClip(message)) return "ready";
  return message.audioId ? "pending" : "none";
}

/**
 * The one message that may start playing by itself, or null.
 *
 * Only the NEWEST message qualifies: when a burst of frames arrives (or a
 * clip lands late, after the learner has already said something else) nothing
 * older ever speaks up. A turn is offered exactly once — `heard` carries the
 * ids we have already played or tried to play — and never while the sound
 * toggle is off or the panel is shut.
 */
export function autoplayCandidate(
  messages: readonly BuddyMessage[],
  ctx: { soundOn: boolean; open: boolean; heard: ReadonlySet<number> },
): BuddyMessage | null {
  if (!ctx.soundOn || !ctx.open) return null;
  const newest = messages[messages.length - 1];
  if (!newest || ctx.heard.has(newest.id) || !playableClip(newest)) return null;
  return newest;
}

/**
 * Re-validate one message read back from sessionStorage. Unknown shapes are
 * dropped, hrefs and clip URLs go through the same guards as the wire, and a
 * clip that was still pending when the tab reloaded is forgotten: that frame
 * can never arrive on this socket, so the control must not wait forever.
 */
export function reviveMessage(raw: unknown): BuddyMessage | null {
  const stored = asRecord(raw);
  if (!stored) return null;
  const { id, role } = stored;
  if (typeof id !== "number" || !Number.isFinite(id)) return null;
  if (role !== "buddy" && role !== "learner") return null;

  const message: BuddyMessage = {
    id,
    role,
    text: typeof stored.text === "string" ? stored.text : "",
  };
  const gloss = nonEmptyString(stored.gloss);
  if (gloss) message.gloss = gloss;
  if (stored.tone === "error") message.tone = "error";

  if (Array.isArray(stored.actions)) {
    const actions = stored.actions
      .map((entry) => {
        const action = asRecord(entry);
        const href = action && action.kind === "navigate" ? safeAppHref(action.href) : null;
        return href
          ? ({
              kind: "navigate",
              href,
              label: nonEmptyString(action?.label) ?? "Take me there",
            } as BuddyAction)
          : null;
      })
      .filter((action): action is BuddyAction => action !== null)
      .slice(0, MAX_ACTIONS);
    if (actions.length) message.actions = actions;
  }

  const audioUrl = safeAudioUrl(stored.audioUrl);
  if (audioUrl) {
    message.audioUrl = audioUrl;
    const audioId = safeClipId(stored.audioId);
    if (audioId) message.audioId = audioId;
  }
  return message;
}
