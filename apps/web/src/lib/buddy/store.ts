"use client";

import { useSyncExternalStore } from "react";
import { buddyWsUrl, getAccessToken } from "@/lib/api/client";
import {
  BUDDY_GREETING,
  BUDDY_OFFLINE,
  BUDDY_SILENCE,
  initialBuddyState,
  prepareOutgoing,
  reduceBuddy,
  reviveMessage,
  type BuddyMessage,
  type BuddyState,
} from "./state";

/**
 * Module-level store for the study buddy, so the conversation survives route
 * changes, panel open/close and even a remount of <BuddyWidget>. Backed by
 * sessionStorage: a hard refresh keeps the chat for the tab's lifetime, a new
 * tab starts fresh, and sign-out wipes it (see resetBuddy).
 *
 * Connection policy:
 *  - lazy: no socket until the panel first opens;
 *  - transparent reconnect on an unexpected drop (bounded backoff);
 *  - closed after IDLE_CLOSE_MS with the panel shut, reopened on the next
 *    open/send — we never hold a socket open forever.
 */

const STORAGE_KEY = "sauti.buddy.v1";
const STORAGE_VERSION = 1;
/**
 * The voice preference outlives the tab, so it lives in localStorage (the
 * conversation itself does not). Absent/unreadable → sound is ON: a learning
 * app whose teacher never speaks is the worse default.
 */
const SOUND_KEY = "sauti.buddy.sound.v1";
/** Panel shut this long → drop the socket. */
const IDLE_CLOSE_MS = 180_000;
/** No frame back after a send → say something rather than spin forever. */
const REPLY_TIMEOUT_MS = 25_000;
const BACKOFF_MS = [400, 1200, 3000, 6000];

export interface BuddySnapshot {
  messages: BuddyMessage[];
  awaiting: boolean;
  open: boolean;
  connected: boolean;
  /** Speaker toggle: when off, replies stay silent unless tapped. */
  soundOn: boolean;
}

let state: BuddyState = initialBuddyState;
let open = false;
let connected = false;
let hydrated = false;
let soundOn = true;

let socket: WebSocket | null = null;
/** Set while we close the socket ourselves — suppresses the reconnect. */
let closingOnPurpose = false;
let attempt = 0;
let outbox: string[] = [];

let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let idleTimer: ReturnType<typeof setTimeout> | null = null;
let replyTimer: ReturnType<typeof setTimeout> | null = null;

const listeners = new Set<() => void>();
let snapshot: BuddySnapshot = {
  messages: [],
  awaiting: false,
  open: false,
  connected: false,
  soundOn: true,
};
const serverSnapshot: BuddySnapshot = snapshot;

function publish() {
  snapshot = {
    messages: state.messages,
    awaiting: state.awaiting,
    open,
    connected,
    soundOn,
  };
  for (const listener of listeners) listener();
}

function persist() {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        v: STORAGE_VERSION,
        messages: state.messages,
        nextId: state.nextId,
      }),
    );
  } catch {
    // Private mode / quota — the chat still works, it just won't survive a reload.
  }
}

function dispatch(event: Parameters<typeof reduceBuddy>[1]) {
  const next = reduceBuddy(state, event);
  if (next === state) return;
  state = next;
  persist();
  publish();
}

/** The stored voice preference, defaulting to ON. */
function readSoundPreference(): boolean {
  try {
    return window.localStorage.getItem(SOUND_KEY) !== "0";
  } catch {
    return true;
  }
}

/** Flip the speaker. Persisted, so it holds across sessions. */
export function setBuddySound(on: boolean) {
  if (soundOn === on) return;
  soundOn = on;
  if (typeof window !== "undefined") {
    try {
      window.localStorage.setItem(SOUND_KEY, on ? "1" : "0");
    } catch {
      // Private mode / quota — the toggle still works for this session.
    }
  }
  publish();
}

/** Read the tab's stored conversation. Called once from the widget's mount. */
export function hydrateBuddy() {
  if (hydrated || typeof window === "undefined") return;
  hydrated = true;
  const storedSound = readSoundPreference();
  if (storedSound !== soundOn) {
    soundOn = storedSound;
    publish();
  }
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const saved = JSON.parse(raw) as {
      v?: number;
      messages?: unknown;
      nextId?: unknown;
    };
    if (saved.v !== STORAGE_VERSION || !Array.isArray(saved.messages)) return;
    // Storage is not the wire, but it isn't our own memory either: every
    // message goes back through the same guards on the way in.
    const messages = saved.messages.map(reviveMessage).filter((m): m is BuddyMessage => m !== null);
    if (!messages.length) return;
    const nextId =
      typeof saved.nextId === "number" ? saved.nextId : Math.max(...messages.map((m) => m.id)) + 1;
    state = { messages, awaiting: false, nextId };
    publish();
  } catch {
    // Corrupt payload: start the session clean rather than crash the shell.
  }
}

// ---------------------------------------------------------------------------
// Socket
// ---------------------------------------------------------------------------

function clearTimer(timer: ReturnType<typeof setTimeout> | null) {
  if (timer) clearTimeout(timer);
  return null;
}

function flush() {
  if (socket?.readyState !== WebSocket.OPEN) return;
  for (const text of outbox) socket.send(JSON.stringify({ text }));
  outbox = [];
}

function scheduleReconnect() {
  if (reconnectTimer || attempt >= BACKOFF_MS.length) return;
  const delay = BACKOFF_MS[attempt++];
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connect();
  }, delay);
}

function connect() {
  if (typeof window === "undefined" || typeof WebSocket === "undefined") return;
  if (
    socket &&
    (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)
  ) {
    return;
  }
  if (!getAccessToken()) {
    // Session bootstrap hasn't minted a token yet — try again shortly.
    scheduleReconnect();
    return;
  }
  closingOnPurpose = false;
  let ws: WebSocket;
  try {
    ws = new WebSocket(buddyWsUrl());
  } catch {
    scheduleReconnect();
    return;
  }
  socket = ws;

  ws.onopen = () => {
    if (socket !== ws) return;
    attempt = 0;
    connected = true;
    publish();
    flush();
  };

  ws.onmessage = (event: MessageEvent) => {
    if (socket !== ws) return;
    replyTimer = clearTimer(replyTimer);
    dispatch({ kind: "frame", frame: event.data });
  };

  ws.onerror = () => {
    // A close event always follows; recovery lives there.
  };

  ws.onclose = () => {
    if (socket !== ws) return;
    socket = null;
    connected = false;
    publish();
    if (closingOnPurpose) return;
    if (outbox.length || open) {
      scheduleReconnect();
      if (attempt >= BACKOFF_MS.length) {
        outbox = [];
        replyTimer = clearTimer(replyTimer);
        dispatch({ kind: "awaiting", value: false });
        dispatch({ kind: "say", text: BUDDY_OFFLINE, tone: "error" });
      }
    }
  };
}

function disconnect() {
  reconnectTimer = clearTimer(reconnectTimer);
  const ws = socket;
  socket = null;
  connected = false;
  if (ws && ws.readyState !== WebSocket.CLOSED) {
    closingOnPurpose = true;
    try {
      ws.close();
    } catch {
      // Already gone.
    }
  }
  publish();
}

function armIdleClose() {
  idleTimer = clearTimer(idleTimer);
  idleTimer = setTimeout(() => {
    idleTimer = null;
    if (!open) disconnect();
  }, IDLE_CLOSE_MS);
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export function openBuddy() {
  idleTimer = clearTimer(idleTimer);
  attempt = 0;
  if (!open) {
    open = true;
    publish();
  }
  // First-ever open gets a free, static hello — no LLM call for an idle peek.
  if (state.messages.length === 0) dispatch({ kind: "say", text: BUDDY_GREETING });
  connect();
}

export function closeBuddy() {
  if (open) {
    open = false;
    publish();
  }
  armIdleClose();
}

export function toggleBuddy() {
  if (open) closeBuddy();
  else openBuddy();
}

/** Send a learner turn; connects (or reconnects) if the socket is away. */
export function sendBuddyMessage(raw: string) {
  const text = prepareOutgoing(raw);
  if (!text) return;
  dispatch({ kind: "learner", text });
  outbox.push(text);
  attempt = 0;
  reconnectTimer = clearTimer(reconnectTimer);
  if (socket?.readyState === WebSocket.OPEN) flush();
  else connect();

  replyTimer = clearTimer(replyTimer);
  replyTimer = setTimeout(() => {
    replyTimer = null;
    dispatch({ kind: "awaiting", value: false });
    dispatch({ kind: "say", text: BUDDY_SILENCE, tone: "error" });
  }, REPLY_TIMEOUT_MS);
}

/** Wipe the conversation and drop the socket (sign-out, tests). */
export function resetBuddy() {
  outbox = [];
  attempt = 0;
  replyTimer = clearTimer(replyTimer);
  idleTimer = clearTimer(idleTimer);
  disconnect();
  open = false;
  state = initialBuddyState;
  if (typeof window !== "undefined") {
    try {
      window.sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      // Nothing to clean up.
    }
  }
  publish();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getSnapshot(): BuddySnapshot {
  return snapshot;
}

/** The current snapshot outside React (tests, imperative callers). */
export function getBuddySnapshot(): BuddySnapshot {
  return snapshot;
}

function getServerSnapshot(): BuddySnapshot {
  return serverSnapshot;
}

export function useBuddy(): BuddySnapshot {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
