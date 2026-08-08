import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

/**
 * Connection behaviour of the buddy store against a fake WebSocket: lazy
 * connect, queue-then-flush, transparent reconnect after a drop, idle close
 * with the panel shut, and sessionStorage persistence across a remount.
 * Module state is global, so every test re-imports through vi.resetModules().
 */

type StoreModule = typeof import("./store");

class FakeSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;
  static instances: FakeSocket[] = [];

  readyState = FakeSocket.CONNECTING;
  sent: string[] = [];
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;

  constructor(readonly url: string) {
    FakeSocket.instances.push(this);
  }

  send(data: string) {
    this.sent.push(data);
  }

  close() {
    if (this.readyState === FakeSocket.CLOSED) return;
    this.readyState = FakeSocket.CLOSED;
    this.onclose?.();
  }

  /** Test helper: the server accepted the socket. */
  accept() {
    this.readyState = FakeSocket.OPEN;
    this.onopen?.();
  }

  /** Test helper: a server frame arrives. */
  emit(frame: unknown) {
    this.onmessage?.({ data: JSON.stringify(frame) });
  }

  /** Test helper: the socket dies without us asking. */
  drop() {
    this.readyState = FakeSocket.CLOSED;
    this.onclose?.();
  }
}

const latest = () => FakeSocket.instances[FakeSocket.instances.length - 1];

async function loadStore(): Promise<StoreModule> {
  vi.resetModules();
  const client = await import("@/lib/api/client");
  client.setAccessToken("test-token");
  return import("./store");
}

describe("buddy store", () => {
  beforeEach(() => {
    FakeSocket.instances = [];
    vi.stubGlobal("WebSocket", FakeSocket);
    window.sessionStorage.clear();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("stays disconnected until the panel is first opened", async () => {
    const store = await loadStore();
    expect(FakeSocket.instances).toHaveLength(0);
    store.openBuddy();
    expect(FakeSocket.instances).toHaveLength(1);
    expect(latest().url).toContain("/ws/buddy?token=test-token");
  });

  it("greets once, for free, on the first open", async () => {
    const store = await loadStore();
    const { BUDDY_GREETING } = await import("./state");
    store.openBuddy();
    latest().accept();
    store.closeBuddy();
    store.openBuddy();

    const stored = JSON.parse(window.sessionStorage.getItem("sauti.buddy.v1")!) as {
      messages: { role: string; text: string }[];
    };
    // Static hello only — one greeting, and nothing spent on the wire.
    expect(stored.messages).toEqual([
      expect.objectContaining({ role: "buddy", text: BUDDY_GREETING }),
    ]);
    expect(latest().sent).toHaveLength(0);
  });

  it("queues a turn sent before the socket opens, then flushes it", async () => {
    const store = await loadStore();
    store.openBuddy();
    store.sendBuddyMessage("  What did I learn today?  ");
    const socket = latest();
    expect(socket.sent).toHaveLength(0);
    socket.accept();
    expect(socket.sent).toEqual([JSON.stringify({ text: "What did I learn today?" })]);
  });

  it("drops empty turns", async () => {
    const store = await loadStore();
    store.openBuddy();
    latest().accept();
    store.sendBuddyMessage("   ");
    expect(latest().sent).toHaveLength(0);
  });

  it("reconnects transparently after an unexpected drop", async () => {
    const store = await loadStore();
    store.openBuddy();
    latest().accept();
    latest().drop();
    expect(FakeSocket.instances).toHaveLength(1);
    vi.advanceTimersByTime(500);
    expect(FakeSocket.instances).toHaveLength(2);
    latest().accept();
    store.sendBuddyMessage("still here?");
    expect(latest().sent).toEqual([JSON.stringify({ text: "still here?" })]);
  });

  it("closes the socket after the panel has been shut a while, and reconnects on the next send", async () => {
    const store = await loadStore();
    store.openBuddy();
    latest().accept();
    store.closeBuddy();
    expect(latest().readyState).toBe(FakeSocket.OPEN);
    vi.advanceTimersByTime(180_000);
    expect(latest().readyState).toBe(FakeSocket.CLOSED);
    expect(FakeSocket.instances).toHaveLength(1); // deliberate close: no reconnect

    store.sendBuddyMessage("back again");
    expect(FakeSocket.instances).toHaveLength(2);
    latest().accept();
    expect(latest().sent).toEqual([JSON.stringify({ text: "back again" })]);
  });

  it("keeps the conversation in sessionStorage for a remount", async () => {
    const store = await loadStore();
    store.openBuddy();
    latest().accept();
    store.sendBuddyMessage("hello");
    latest().emit({ type: "buddy", text: "Muraho!", gloss: "Hello!" });
    latest().emit({
      type: "action",
      action: { kind: "navigate", href: "/vocab", label: "Take me there" },
    });

    const fresh = await loadStore();
    fresh.hydrateBuddy();
    const stored = JSON.parse(window.sessionStorage.getItem("sauti.buddy.v1")!) as {
      messages: { role: string; text: string; actions?: unknown[] }[];
    };
    const roles = stored.messages.map((m) => m.role);
    expect(roles).toEqual(["buddy", "learner", "buddy"]); // greeting, turn, reply
    expect(stored.messages[2].actions).toHaveLength(1);
  });

  it("wipes the conversation and the socket on reset", async () => {
    const store = await loadStore();
    store.openBuddy();
    latest().accept();
    store.sendBuddyMessage("hello");
    store.resetBuddy();
    expect(latest().readyState).toBe(FakeSocket.CLOSED);
    expect(window.sessionStorage.getItem("sauti.buddy.v1")).toBeNull();
  });
});
