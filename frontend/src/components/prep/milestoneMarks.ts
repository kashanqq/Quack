"use client";

// Ticking a milestone done — the one tick in the product (product-logic §4.1) — and picking the test date
// a registration belongs to. Both have several ways in with the same effect: the choice chat, the Quack
// calendar and feed, «Подготовка → Требования». Outside «Подготовки» they write the preparation state
// here and tell Quack at once, so the forecast and the signals follow.

import { useSyncExternalStore } from "react";
import { store } from "../account/store";
import { quackSource } from "../quack/source";
import type { DatedExam, TestDates } from "./prepData";
import { chooseTestDate, initialModel, reviveModel, type PrepModel } from "./prepModel";

const PREP_KEY = "quack-prep";
const NO_MARKS: string[] = [];
const NO_DATES: TestDates = {};

const listeners = new Set<() => void>();
// Handed out as long as the stored state is the same object, so screens re-render only on a change
let lastRaw: unknown = undefined;
let marks: string[] = NO_MARKS;
let dates: TestDates = NO_DATES;

function refresh() {
  const raw = store.get<PrepModel>(PREP_KEY);
  if (raw === lastRaw) return;
  lastRaw = raw;
  marks = raw?.milestonesDone ?? NO_MARKS;
  dates = raw?.testDates ?? NO_DATES;
}

/** The ticked milestone ids, as stored now. */
export function doneMilestones(): string[] {
  refresh();
  return marks;
}

/** The test date picked per exam, as stored now. */
export function chosenTestDates(): TestDates {
  refresh();
  return dates;
}

function update(change: (model: PrepModel) => PrepModel) {
  const next = change(reviveModel(store.get(PREP_KEY)) ?? initialModel());
  store.set(PREP_KEY, next);
  quackSource().report({ prep: next });
  listeners.forEach((listener) => listener());
}

/** Sets a milestone done (or not); the default flips it. Returns whether it is done afterwards. */
export function markMilestone(id: string, done?: boolean): boolean {
  const has = doneMilestones().includes(id);
  const want = done ?? !has;
  if (want !== has) {
    update((model) => ({
      ...model,
      milestonesDone: want ? [...model.milestonesDone, id] : model.milestonesDone.filter((m) => m !== id),
    }));
  }
  return want;
}

/** Picks the sitting of an exam by its `dateKey`; null goes back to the nearest one. */
export function pickTestDate(exam: DatedExam, key: string | null) {
  if ((chosenTestDates()[exam] ?? null) === key) return;
  update((model) => chooseTestDate(model, exam, key));
}

const subscribe = (listener: () => void) => {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
};

/** The ticked milestones for a screen; it re-renders on every tick, wherever it was made. */
export function useDoneMilestones(): string[] {
  return useSyncExternalStore(subscribe, doneMilestones, () => NO_MARKS);
}

/** The picked test dates for a screen; it re-renders on every pick, wherever it was made. */
export function useChosenTestDates(): TestDates {
  return useSyncExternalStore(subscribe, chosenTestDates, () => NO_DATES);
}
