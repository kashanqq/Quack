// Everything the client remembers for the signed-in student: chats and profile, saved programs,
// preparation, what Quack has shown, panel widths, where the skill map was left. One place, keyed by
// student, so signing out and back in brings back exactly what was there.
//
// Reads are synchronous, from a cache filled once when the student signs in (AuthGate waits for it).
// Writes land in the cache at once and reach the backend shortly after, coalesced per key: a typing
// reply or a burst of edits is one write, not one per frame. Anything still pending goes out when the
// tab is hidden or closed. Continuous gestures (panning, dragging, resizing) call `set` only when they
// end — the screens keep the in-between state to themselves.

import type { StateBackend, User } from "./contract";

const REMOTE = process.env.NEXT_PUBLIC_DATA_SOURCE === "remote";
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
/** Local storage is cheap; the network gets a longer pause to gather more into one request */
const FLUSH_MS = REMOTE ? 1200 : 250;

/* ---------- Backends ---------- */

const prefix = (userId: string) => `quack:u:${userId}:`;

/** Keys from before accounts existed. The first account signed in on this browser takes them over */
const LEGACY = /^(quack-|lupidrupi\.)/;
/** Keys that belong to the device, not to a student */
const DEVICE = new Set(["quack-accounts", "quack-session", "quack-demo-shift", "quack-pending-cause"]);

const localBackend: StateBackend = {
  async load(userId) {
    const out: Record<string, unknown> = {};
    const p = prefix(userId);
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i)!;
        if (!key.startsWith(p)) continue;
        try {
          out[key.slice(p.length)] = JSON.parse(localStorage.getItem(key)!);
        } catch {}
      }
      if (!Object.keys(out).length) adoptLegacy(userId, out);
    } catch {}
    return out;
  },
  async save(userId, entries) {
    this.saveOnExit(userId, entries);
  },
  saveOnExit(userId, entries) {
    const p = prefix(userId);
    for (const [key, value] of Object.entries(entries)) {
      try {
        if (value === null) localStorage.removeItem(p + key);
        else localStorage.setItem(p + key, JSON.stringify(value));
      } catch {
        // Full or private mode: this visit still works, it just is not remembered
      }
    }
  },
  async clear(userId) {
    const p = prefix(userId);
    try {
      const keys = Array.from({ length: localStorage.length }, (_, i) => localStorage.key(i)!);
      keys.filter((k) => k.startsWith(p)).forEach((k) => localStorage.removeItem(k));
    } catch {}
  },
};

/** Moves what this browser kept before sign-in existed into the first account, once */
function adoptLegacy(userId: string, into: Record<string, unknown>) {
  const keys = Array.from({ length: localStorage.length }, (_, i) => localStorage.key(i)!);
  for (const key of keys) {
    if (!LEGACY.test(key) || DEVICE.has(key)) continue;
    try {
      const value = JSON.parse(localStorage.getItem(key)!);
      into[key] = value;
      localStorage.setItem(prefix(userId) + key, JSON.stringify(value));
    } catch {}
    localStorage.removeItem(key);
  }
}

const remoteBackend: StateBackend = {
  async load() {
    const res = await fetch(`${API}/state`, { credentials: "include" });
    if (!res.ok) throw new Error(`state ${res.status}`);
    return res.json();
  },
  async save(_userId, entries) {
    await fetch(`${API}/state`, {
      method: "PATCH",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(entries),
    });
  },
  saveOnExit(_userId, entries) {
    // keepalive lets the request finish after the page is gone
    void fetch(`${API}/state`, {
      method: "PATCH",
      credentials: "include",
      keepalive: true,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(entries),
    }).catch(() => undefined);
  },
  async clear() {
    await fetch(`${API}/state`, { method: "DELETE", credentials: "include" });
  },
};

const backend = REMOTE ? remoteBackend : localBackend;

/* ---------- The cache the screens read ---------- */

let userId: string | null = null;
let cache: Record<string, unknown> = {};
let pending: Record<string, unknown> = {};
let timer: ReturnType<typeof setTimeout> | null = null;

function takePending() {
  const batch = pending;
  pending = {};
  if (timer) clearTimeout(timer);
  timer = null;
  return Object.keys(batch).length ? batch : null;
}

function flush() {
  const batch = takePending();
  if (batch && userId) backend.save(userId, batch).catch(() => {
    // Back into the queue for the next attempt, unless a newer value came meanwhile
    pending = { ...batch, ...pending };
  });
}

function flushOnExit() {
  const batch = takePending();
  if (batch && userId) backend.saveOnExit(userId, batch);
}

if (typeof window !== "undefined") {
  window.addEventListener("pagehide", flushOnExit);
  document.addEventListener("visibilitychange", () => document.visibilityState === "hidden" && flushOnExit());
}

export const store = {
  /** Loads the student's state; everything else in the app waits for this */
  async open(user: User) {
    if (userId === user.id) return;
    flushOnExit();
    cache = await backend.load(user.id);
    userId = user.id;
  },

  /** Drops the cache on sign-out, after sending what is still pending */
  close() {
    flushOnExit();
    userId = null;
    cache = {};
  },

  get<T>(key: string): T | null {
    return key in cache ? (cache[key] as T) : null;
  },

  /** null removes the key */
  set(key: string, value: unknown) {
    if (value === null || value === undefined) delete cache[key];
    else cache[key] = value;
    pending[key] = value ?? null;
    if (!timer) timer = setTimeout(flush, FLUSH_MS);
  },

  /** "Начать заново": the student's data goes, the account stays */
  async reset() {
    takePending();
    cache = {};
    if (userId) await backend.clear(userId);
  },
};
