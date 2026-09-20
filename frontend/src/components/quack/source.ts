"use client";

// Where the Quack state comes from. The screens call useQuack() and never know which source runs:
//   local  — the browser recomputes on every change (default, works without a backend);
//   remote — the backend recomputes and pushes the state over SSE.
// Switch with NEXT_PUBLIC_QUACK_SOURCE=remote and NEXT_PUBLIC_API_URL=<api base>.

import { useSyncExternalStore } from "react";
import { EMPTY_STATE, type QuackState } from "./contract";
import { localSource } from "./localSource";
import { remoteSource } from "./remoteSource";
import type { QuackInputs } from "./standing";

export interface QuackSource {
  subscribe(listener: () => void): () => void;
  getSnapshot(): QuackState;
  /** A source of truth changed on this device: pass the slices that changed. */
  report(change: Partial<QuackInputs>): void;
  /** The student opened Quack and saw the state: what is fresh becomes history, the glow goes out. */
  markSeen(): void;
  /** «Начать заново»: forget the baseline and the history. */
  reset(): void;
  /** Take a backend recommendation: the plan changes server-side. Absent for the local source. */
  accept?(id: string): Promise<void>;
  /** Turn one down, with the student's reason when they gave one. */
  decline?(id: string, reason?: string): Promise<void>;
}

let instance: QuackSource | null = null;

export function quackSource(): QuackSource {
  if (!instance) {
    // Still an explicit switch, not NEXT_PUBLIC_DATA_SOURCE. remoteSource speaks the phase 4 API, but
    // /quack has no readiness and no per-program chances — those come from /overview and /matching,
    // and until the dashboard reads them (F3.3) the general flag would empty the cards it fills today.
    instance = process.env.NEXT_PUBLIC_QUACK_SOURCE === "remote" ? remoteSource() : localSource();
  }
  return instance;
}

const serverSnapshot = () => EMPTY_STATE;

/** The Quack state for a screen, plus the two things a screen can tell it. */
export function useQuack() {
  const source = quackSource();
  const state = useSyncExternalStore(source.subscribe, source.getSnapshot, serverSnapshot);
  return {
    state,
    report: source.report,
    markSeen: source.markSeen,
    reset: source.reset,
    /** Only the remote source can decide a recommendation; local signals have nothing to post */
    decide: source.accept && source.decline ? { accept: source.accept, decline: source.decline } : null,
  };
}
