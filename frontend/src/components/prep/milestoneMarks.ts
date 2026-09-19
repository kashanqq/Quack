"use client";

// Ticking a milestone done — the one tick in the product (product-logic §4.1). It has three ways in with
// the same effect: the choice chat, the calendar and the Quack feed. All of them write the preparation
// state here and tell Quack at once, so the forecast and the signals follow the tick.

import { useSyncExternalStore } from "react";
import { store } from "../account/store";
import { quackSource } from "../quack/source";
import { initialModel, reviveModel, type PrepModel } from "./prepModel";

const PREP_KEY = "quack-prep";
const NONE: string[] = [];

const listeners = new Set<() => void>();
// The list is handed out as long as the stored state is the same object, so screens re-render only on a change
let lastRaw: unknown = undefined;
let snapshot: string[] = NONE;

/** The ticked milestone ids, as stored now. */
export function doneMilestones(): string[] {
  const raw = store.get<PrepModel>(PREP_KEY);
  if (raw !== lastRaw) {
    lastRaw = raw;
    snapshot = raw?.milestonesDone ?? NONE;
  }
  return snapshot;
}

/** Sets a milestone done (or not); the default flips it. Returns whether it is done afterwards. */
export function markMilestone(id: string, done?: boolean): boolean {
  const model = reviveModel(store.get(PREP_KEY)) ?? initialModel();
  const has = model.milestonesDone.includes(id);
  const want = done ?? !has;
  if (want === has) return has;
  const next: PrepModel = {
    ...model,
    milestonesDone: want ? [...model.milestonesDone, id] : model.milestonesDone.filter((m) => m !== id),
  };
  store.set(PREP_KEY, next);
  quackSource().report({ prep: next });
  listeners.forEach((listener) => listener());
  return want;
}

const subscribe = (listener: () => void) => {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
};

/** The ticked milestones for a screen; it re-renders on every tick, wherever it was made. */
export function useDoneMilestones(): string[] {
  return useSyncExternalStore(subscribe, doneMilestones, () => NONE);
}
