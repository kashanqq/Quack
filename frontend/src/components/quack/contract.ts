// What the Quack! screen and button show, as one JSON-safe shape. Today the browser computes it
// (localSource); later the backend does and pushes it over SSE (remoteSource). The screens only
// read this shape, so switching the source does not touch them. Keep in sync with the backend schema.
//
// Flow (arch-logic §02 «изменил → изменилось»): a source of truth changes (profile, saved programs,
// preparation) → the rules recompute the standing → the planner compares it with what the student
// saw on their last visit → whatever differs becomes a signal and the button glows until they look.

import type { Level } from "../choice/programs";

/** 0 не успеваешь · 1 нужно ускориться · 2 успеваешь · 3 с запасом */
export type PaceLevel = 0 | 1 | 2 | 3;

/** One exam: will the student be ready by the test, and what to do if not. */
export type ExamPace = {
  id: string;
  name: string;
  level: PaceLevel;
  verdict: string;
  /** One sentence with the numbers behind the verdict */
  summary: string;
  /** Concrete steps, each with its effect; empty when all is well */
  advice: string[];
  /** The bar the saved programs set, e.g. "650" or "6.5" */
  target?: string;
  /** ISO date of the planned test */
  testDate?: string;
  /** ISO date the knowledge model expects readiness; absent for exams without a model */
  forecast?: string;
};

export type ChanceFact = {
  key: "sat" | "sat-forecast" | "ielts" | "budget";
  label: string;
  have: string;
  need: string;
  ok: boolean | null;
  /** How far above (+) or below (−) the bar, in the fact's own units; null when unknown */
  margin: number | null;
};

/** A saved program as the rules see it now. Chances are words, never percentages (product-logic §1). */
export type ProgramChance = {
  id: string;
  university: string;
  level: Level;
  levelLabel: string;
  /** Internal ordering: only the direction of its change is ever shown */
  index: number;
  facts: ChanceFact[];
};

export type StandingAlert = {
  id: string;
  level: SignalLevel;
  kind: "deadline" | "missed" | "conflict" | "late-set";
  title: string;
  detail?: string;
};

/** Everything derived from the sources of truth at one moment. */
export type Standing = {
  /** The day the standing was computed for, ISO */
  asOf: string;
  /** Preparation readiness, % */
  readiness: number;
  /** The worst exam decides; null while nothing is saved */
  pace: { level: PaceLevel; verdict: string; summary: string; advice: string[]; exam: string } | null;
  exams: ExamPace[];
  programs: ProgramChance[];
  alerts: StandingAlert[];
  next?: { title: string; date: string; daysLeft: number };
};

export type SignalLevel = "urgent" | "notice";

/** Something that changed since the student last opened Quack. */
export type Signal = {
  id: string;
  level: SignalLevel;
  /** up — got better, down — got worse, info — neither */
  tone: "up" | "down" | "info";
  kind: "chance" | "pace" | "deadline" | "missed" | "conflict" | "late-set" | "programs";
  title: string;
  detail?: string;
  /** What the student did that caused it, when known */
  cause?: string;
  /** Program or exam id the signal is about */
  subject?: string;
  /** ISO time it was first noticed */
  at: string;
  /** Where to go to deal with it */
  target?: "prep" | "calendar" | "programs" | "profile";
};

export type QuackState = {
  standing: Standing | null;
  /** Not seen yet: these make the Quack! button glow */
  fresh: Signal[];
  /** Seen on earlier visits, newest first */
  history: Signal[];
  glow: SignalLevel | null;
  /** local — computed in the browser; live — pushed by the backend */
  status: "local" | "connecting" | "live" | "offline";
};

export const EMPTY_STATE: QuackState = { standing: null, fresh: [], history: [], glow: null, status: "local" };

export const glowOf = (signals: Signal[]): SignalLevel | null =>
  signals.some((s) => s.level === "urgent") ? "urgent" : signals.length ? "notice" : null;
