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
    // The domain flag wins over the general one, as it does in prep/remoteSets.ts; without either the
    // browser recomputes, so the app still runs with no backend at all.
    const flag = process.env.NEXT_PUBLIC_QUACK_SOURCE ?? process.env.NEXT_PUBLIC_DATA_SOURCE;
    instance = flag === "remote" ? remoteSource() : localSource();
  }
  return instance;
}

const serverSnapshot = () => EMPTY_STATE;

/** The Quack state for a screen, plus the two things a screen can tell it. */
export function useQuack() {
  const source = quackSource();
  const state = useSyncExternalStore(source.subscribe, source.getSnapshot, serverSnapshot);
  return { state, report: source.report, markSeen: source.markSeen, reset: source.reset };
}
