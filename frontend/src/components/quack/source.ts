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
}

let instance: QuackSource | null = null;

export function quackSource(): QuackSource {
  if (!instance) {
    // Only an explicit switch: the backend's /quack API (phase 4) does not speak remoteSource's contract
    // yet (/quack/state + SSE), so with DATA_SOURCE=remote the browser still recomputes — from the
    // profile, saved programs and realism that now come from the backend.
    const isRemote = process.env.NEXT_PUBLIC_QUACK_SOURCE === "remote";
    instance = isRemote
      ? remoteSource(process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000")
      : localSource();
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
