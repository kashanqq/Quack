// The Quack source for when the backend recomputes (arch-logic: events store → rules → SSE).
// Not active by default; see source.ts for the switch. The contract it expects:
//
//   GET  {api}/quack/state        → QuackState (contract.ts), the current standing, fresh and history
//   GET  {api}/sse?topics=quack    → SSE stream; event "quack" carries a full QuackState after every recompute
//   POST {api}/events              ← { type: "profile.changed" | "saved.changed" | "prep.changed", payload }
//   POST {api}/quack/seen          ← the student opened Quack; the server moves its baseline
//
// Until every action has its own endpoint, report() forwards the changed slices as events, so the
// backend can recompute from them. The server owns the baseline, the signals and the glow.

import { EMPTY_STATE, type QuackState } from "./contract";
import type { QuackSource } from "./source";

const EVENT_TYPE = { profile: "profile.changed", saved: "saved.changed", prep: "prep.changed" } as const;

export function remoteSource(api: string): QuackSource {
  let state: QuackState = { ...EMPTY_STATE, status: "connecting" };
  let stream: EventSource | null = null;
  const listeners = new Set<() => void>();

  const set = (next: QuackState) => {
    state = next;
    listeners.forEach((listener) => listener());
  };

  const connect = () => {
    fetch(`${api}/quack/state`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((next: QuackState) => set({ ...next, status: "live" }))
      .catch(() => set({ ...state, status: "offline" }));

    stream = new EventSource(`${api}/sse?topics=quack`, { withCredentials: true });
    stream.addEventListener("quack", (e) => set({ ...(JSON.parse((e as MessageEvent).data) as QuackState), status: "live" }));
    // EventSource reconnects by itself; until then the last known state stays on screen
    stream.onerror = () => set({ ...state, status: "offline" });
  };

  const post = (path: string, body?: unknown) =>
    fetch(`${api}${path}`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    }).catch(() => set({ ...state, status: "offline" }));

  return {
    subscribe(listener) {
      listeners.add(listener);
      if (!stream) connect();
      return () => {
        listeners.delete(listener);
        if (!listeners.size) {
          stream?.close();
          stream = null;
        }
      };
    },

    getSnapshot: () => state,

    report(change) {
      for (const key of Object.keys(change) as (keyof typeof EVENT_TYPE)[]) {
        post("/events", { type: EVENT_TYPE[key], payload: change[key] });
      }
    },

    markSeen() {
      if (state.fresh.length) post("/quack/seen");
    },

    reset() {},
  };
}
