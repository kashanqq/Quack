// The Quack source that reads the backend's phase-4 API instead of recomputing in the browser.
//
//   GET  /quack                    → pace, feed, activity, and whether a new batch is waiting
//   POST /quack/seen               → opening the screen; pending items become shown, the glow goes out
//   POST /quack/{id}/accept        → take the recommendation; the rules change the plan server-side
//   POST /quack/{id}/decline       → keep it out of the feed
//
// There is no push channel: `/sse` serves the chat and nothing else, and there is no `/events` router
// at all — the backend writes its own events from the domain endpoints. So the state is re-read when
// it can plausibly have changed: on the first subscriber, when the tab comes back, once a minute, and
// right after anything this device did to a source of truth (report()).
//
// What this source cannot know on its own — readiness, saved-program chances, the calendar — stays out
// of the standing here; the dashboard reads it from /overview and /matching.

import { backend } from "@/api/backend";
import { EMPTY_STATE, glowOf, type QuackState, type Signal, type Standing } from "./contract";
import { toQuackView, type QuackView } from "./remoteAdapter";
import type { QuackSource } from "./source";

/** A quiet tab is still worth a look now and then: the server recomputes on its own schedule */
const POLL_MS = 60_000;
/** Requests coalesce: a burst of reports is one read, not one per report */
const DEBOUNCE_MS = 400;
const HISTORY_MAX = 12;

/** The part of the standing this API can speak for; the rest is the dashboard's to fill in */
function standingOf(view: QuackView): Standing {
  return {
    asOf: view.asOf,
    readiness: 0,
    pace: view.pace
      ? {
          level: view.pace.level,
          verdict: view.pace.verdict,
          summary: view.pace.summary,
          advice: view.pace.advice,
          exam: view.pace.id,
          adviceActions: view.pace.adviceActions,
        }
      : null,
    exams: view.exams,
    programs: [],
    alerts: [],
  };
}

export function remoteSource(): QuackSource {
  let state: QuackState = { ...EMPTY_STATE, status: "connecting" };
  let history: Signal[] = [];
  let timer: ReturnType<typeof setTimeout> | null = null;
  let poll: ReturnType<typeof setInterval> | null = null;
  let inFlight: Promise<void> | null = null;
  const listeners = new Set<() => void>();

  const emit = () => listeners.forEach((listener) => listener());

  const set = (next: QuackState) => {
    state = next;
    emit();
  };

  async function load(): Promise<void> {
    try {
      const view = toQuackView(await backend.quack.get());
      // Decided items leave the feed; what the student has already been shown becomes the history
      const seen = view.open.filter((s) => !view.fresh.some((f) => f.id === s.id));
      history = [...seen, ...history.filter((h) => !view.open.some((o) => o.id === h.id))].slice(0, HISTORY_MAX);
      set({ standing: standingOf(view), fresh: view.fresh, history, glow: glowOf(view.fresh), status: "live" });
    } catch {
      // Nothing is thrown away: the last known state stays on screen, marked as out of date
      set({ ...state, status: "offline" });
    }
  }

  /** One read at a time, and at most one per DEBOUNCE_MS however many callers ask */
  function refresh() {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      timer = null;
      inFlight = (inFlight ?? Promise.resolve()).then(load, load);
    }, DEBOUNCE_MS);
  }

  const onFocus = () => document.visibilityState === "visible" && refresh();

  return {
    subscribe(listener) {
      listeners.add(listener);
      if (listeners.size === 1) {
        refresh();
        poll = setInterval(refresh, POLL_MS);
        document.addEventListener("visibilitychange", onFocus);
      }
      return () => {
        listeners.delete(listener);
        if (!listeners.size) {
          if (poll) clearInterval(poll);
          poll = null;
          document.removeEventListener("visibilitychange", onFocus);
        }
      };
    },

    getSnapshot: () => state,

    /**
     * A source of truth changed on this device. The change itself has already gone to its own endpoint
     * (profile, saved, sets, tasks), which is what writes the event — this only asks for the result.
     */
    report() {
      refresh();
    },

    markSeen() {
      const pending = state.fresh.map((s) => s.id);
      if (!pending.length) return;
      // Optimistic: the glow goes out now, the server catches up and the next read confirms it
      history = [...state.fresh, ...history.filter((h) => !pending.includes(h.id))].slice(0, HISTORY_MAX);
      set({ ...state, fresh: [], history, glow: null });
      backend.quack.seen(pending).then(refresh, refresh);
    },

    accept(id) {
      return backend.quack.accept(id).then(
        () => {
          refresh();
        },
        (e) => {
          refresh();
          throw e;
        },
      );
    },

    decline(id, reason) {
      return backend.quack.decline(id, reason).then(
        () => {
          refresh();
        },
        (e) => {
          refresh();
          throw e;
        },
      );
    },

    reset() {
      history = [];
      set({ ...EMPTY_STATE, status: "connecting" });
      refresh();
    },
  };
}
