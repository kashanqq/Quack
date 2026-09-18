// State of the "Подготовка" section and the rules that change it. Pure functions, no React:
// a self-check answer is evidence, evidence moves skill state, a set is passed when all its skills are solid.

import {
  SETS,
  SKILLS,
  TODAY,
  type Evidence,
  type ExamId,
  type Misconception,
  type SetStatus,
  type SkillState,
  type StudySet,
  type Task,
} from "./prepData";

import type { IconName } from "../choice/Icon";

export type PrepTab = "overview" | "sets";

export const PREP_TABS: { tab: PrepTab; label: string; icon: IconName }[] = [
  { tab: "overview", label: "Обзор", icon: "layout-dashboard" },
  { tab: "sets", label: "Сеты", icon: "route" },
];

/**
 * Every tab holds several separate things, so each one is split further: the tab says which part of
 * preparation you are in, the sub-tab says what you are looking at. The left column shows both.
 */
export type PrepSub = "now" | "requirements" | "list" | "route" | "map";

export const PREP_SUBS: Record<PrepTab, { sub: PrepSub; label: string; icon: IconName; hint: string }[]> = {
  overview: [
    { sub: "now", label: "Сейчас", icon: "target", hint: "что делать и темп" },
    { sub: "requirements", label: "Требования", icon: "gauge", hint: "цели экзаменов и прогноз" },
  ],
  sets: [
    { sub: "list", label: "Все сеты", icon: "layers", hint: "три рекомендованных сверху" },
    { sub: "route", label: "Маршрут", icon: "route", hint: "сеты по датам" },
    { sub: "map", label: "Карта навыков", icon: "network", hint: "все темы экзамена" },
  ],
};

/** Keeps a sub-tab that belongs to another tab from leaking in; falls back to the tab's first one. */
export const subFor = (tab: PrepTab, sub: PrepSub): PrepSub =>
  PREP_SUBS[tab].some((s) => s.sub === sub) ? sub : PREP_SUBS[tab][0].sub;

export type PrepModel = {
  states: Record<string, SkillState>;
  recall: Record<string, number>;
  misconceptions: Record<string, Misconception[]>;
  evidence: Record<string, Evidence[]>;
  doneSets: string[];
  /** null while the next set is only proposed */
  currentSet: string | null;
  /** Days the forecast moved because of manual changes */
  extraDays: number;
  milestonesDone: string[];
  resolvedConflicts: Record<string, string>;
  /** Show the section on demo programs when nothing is saved */
  demo: boolean;
  /** Last set whose report hasn't been dismissed */
  reportFor: string | null;
};

export function initialModel(): PrepModel {
  return {
    states: Object.fromEntries(SKILLS.map((s) => [s.id, s.state])),
    recall: Object.fromEntries(SKILLS.map((s) => [s.id, s.recall])),
    misconceptions: Object.fromEntries(SKILLS.map((s) => [s.id, s.misconceptions])),
    evidence: Object.fromEntries(SKILLS.map((s) => [s.id, s.evidence])),
    doneSets: ["s1"],
    currentSet: null,
    extraDays: 0,
    milestonesDone: [],
    resolvedConflicts: {},
    demo: false,
    reportFor: "s1",
  };
}

/** Stored state keeps dates as strings (JSON); bring them back. */
export function reviveModel(raw: unknown): PrepModel | null {
  if (!raw || typeof raw !== "object") return null;
  const fresh = initialModel();
  const saved = raw as Partial<PrepModel>;
  // Per-skill records are merged, not replaced: a model saved before a skill (or a whole exam) was
  // added still gets that skill's starting state
  const model: PrepModel = {
    ...fresh,
    ...saved,
    states: { ...fresh.states, ...saved.states },
    recall: { ...fresh.recall, ...saved.recall },
    misconceptions: { ...fresh.misconceptions, ...saved.misconceptions },
    evidence: { ...fresh.evidence, ...saved.evidence },
  };
  model.evidence = Object.fromEntries(
    Object.entries(model.evidence).map(([id, list]) => [id, list.map((e) => ({ ...e, date: new Date(e.date) }))])
  );
  return model;
}

export function setStatus(model: PrepModel, set: StudySet): SetStatus | "proposed" {
  if (model.doneSets.includes(set.id)) return "done";
  if (model.currentSet === set.id) return "current";
  if (!model.currentSet && proposedSet(model)?.id === set.id) return "proposed";
  return set.status === "review" ? "review" : "upcoming";
}

/**
 * Why a set is worth taking now, from what the model knows about the student: roots of errors,
 * confirmed traps, skills that do not hold. A set leaning on skills that are not there yet goes lower.
 */
export type Recommendation = { set: StudySet; score: number; reasons: string[] };

const GAP: Record<SkillState, number> = { weak: 1, lowData: 0.6, shaky: 0.5, solid: 0 };

export function rankSets(model: PrepModel, exam: ExamId): Recommendation[] {
  return SETS.filter((s) => s.exam === exam && !model.doneSets.includes(s.id))
    .map((set) => {
      const reasons: string[] = [];
      let score = 0;
      for (const id of set.skills) {
        const skill = SKILLS.find((s) => s.id === id)!;
        const state = model.states[id];
        score += GAP[state] * skill.weight;
        if (state === "solid") continue;
        if (skill.root) {
          score += 30;
          reasons.push(`корень ошибок: ${skill.name}`);
        }
        const traps = model.misconceptions[id].filter((m) => m.status === "confirmed");
        if (traps.length) {
          score += 25;
          reasons.push(`подтверждённая ловушка: ${skill.name}`);
        } else if (state === "weak") {
          reasons.push(`не держится: ${skill.name}`);
        }
      }
      // Prerequisites outside the set that do not hold yet: the set would be built on sand
      const missing = [
        ...new Set(
          set.skills.flatMap((id) => SKILLS.find((s) => s.id === id)!.requires).filter((id) => !set.skills.includes(id) && model.states[id] !== "solid")
        ),
      ];
      score -= missing.length * 12;
      if (missing.length) reasons.push(`сначала нужно: ${missing.map((id) => SKILLS.find((s) => s.id === id)!.name).join(", ")}`);
      // Review comes last by design: no new skills in it
      if (set.status === "review") score -= 40;
      if (!reasons.length) {
        const open = set.skills.filter((id) => model.states[id] !== "solid").length;
        reasons.push(open ? `осталось доказать тем: ${open} из ${set.skills.length}` : "всё уже держится — повторение");
      }
      return { set, score, reasons };
    })
    .sort((a, b) => b.score - a.score);
}

/** The next set the system recommends: the first one in the route that isn't passed. */
export function proposedSet(model: PrepModel): StudySet | undefined {
  return SETS.find((s) => !model.doneSets.includes(s.id) && s.id !== model.currentSet);
}

export const closed = (model: PrepModel, set: StudySet) => set.skills.filter((id) => model.states[id] === "solid").length;

/** Readiness for one exam: weighted share of its solid skills, shaky counts half. */
export function readiness(model: PrepModel, exam: ExamId = "sat"): number {
  const skills = SKILLS.filter((s) => s.exam === exam);
  const total = skills.reduce((sum, s) => sum + s.weight, 0);
  const got = skills.reduce(
    (sum, s) => sum + s.weight * (model.states[s.id] === "solid" ? 1 : model.states[s.id] === "shaky" ? 0.5 : 0),
    0
  );
  return Math.round((got / total) * 100);
}

export function acceptSet(model: PrepModel, id: string): PrepModel {
  return { ...model, currentSet: id, reportFor: null };
}

/** Choosing a set out of the recommended order costs a few days of forecast. */
export function makeCurrent(model: PrepModel, id: string): { model: PrepModel; shift: number } {
  const recommended = proposedSet({ ...model, currentSet: null });
  const shift = recommended && recommended.id !== id ? 3 : 0;
  const doneSets = model.doneSets.filter((s) => s !== id);
  return { model: { ...model, currentSet: id, doneSets, extraDays: model.extraDays + shift, reportFor: null }, shift };
}

const UP: Record<SkillState, SkillState> = { weak: "shaky", lowData: "shaky", shaky: "solid", solid: "solid" };

export type AnswerResult = {
  model: PrepModel;
  correct: boolean;
  trap?: string;
  from: SkillState;
  to: SkillState;
  setPassed?: StudySet;
};

/** A task answer becomes evidence; correct answers raise the state, trap answers feed the misconception. */
export function answerTask(model: PrepModel, skillId: string, task: Task, optionIndex: number): AnswerResult {
  const option = task.options[optionIndex];
  const from = model.states[skillId];
  const to = option.correct ? UP[from] : from === "solid" ? "shaky" : from;

  const evidence: Evidence = {
    source: "проверка",
    text: `${task.text.slice(0, 60)}… — ответ ${option.label}${option.correct ? ", верно" : option.trap ? `, ловушка: ${option.trap.toLowerCase()}` : ", неверно"}`,
    date: TODAY,
  };

  let misconceptions = model.misconceptions[skillId];
  if (!option.correct && option.trap) {
    const existing = misconceptions.find((m) => m.text.toLowerCase().includes(option.trap!.toLowerCase().slice(0, 12)));
    if (existing) {
      misconceptions = misconceptions.map((m) =>
        m === existing ? { ...m, observations: m.observations + 1, status: m.observations + 1 >= 2 ? "confirmed" : "suspected" } : m
      );
    } else {
      misconceptions = [
        ...misconceptions,
        { id: `${skillId}-${task.id}`, text: option.trap, status: "suspected", observations: 1 },
      ];
    }
  } else if (option.correct) {
    // Getting past the trap once the skill is solid counts as "исправлено, следим"
    misconceptions = misconceptions.map((m) =>
      m.status === "confirmed" && to === "solid" && task.options.some((o) => o.trap) ? { ...m, status: "resolved" } : m
    );
  }

  const recall = option.correct ? Math.min(0.95, model.recall[skillId] + 0.2) : Math.max(0.2, model.recall[skillId] - 0.1);

  let next: PrepModel = {
    ...model,
    states: { ...model.states, [skillId]: to },
    recall: { ...model.recall, [skillId]: recall },
    misconceptions: { ...model.misconceptions, [skillId]: misconceptions },
    evidence: { ...model.evidence, [skillId]: [evidence, ...model.evidence[skillId]] },
  };

  // Any open set with this topic may be complete now — not only the current one
  let setPassed: StudySet | undefined;
  for (const set of SETS.filter((s) => s.skills.includes(skillId) && !next.doneSets.includes(s.id))) {
    if (closed(next, set) === set.skills.length) {
      setPassed = set;
      next = {
        ...next,
        doneSets: [...next.doneSets, set.id],
        currentSet: next.currentSet === set.id ? null : next.currentSet,
        reportFor: set.id,
      };
    }
  }

  return { model: next, correct: Boolean(option.correct), trap: option.trap, from, to, setPassed };
}

/** "Не согласен": the misconception leaves sets and chat context until new evidence. */
export function disputeMisconception(model: PrepModel, skillId: string, id: string): PrepModel {
  return {
    ...model,
    misconceptions: {
      ...model.misconceptions,
      [skillId]: model.misconceptions[skillId].map((m) => (m.id === id ? { ...m, status: "disputed" } : m)),
    },
  };
}

export const MISCONCEPTION_LABEL = (m: Misconception) =>
  m.status === "confirmed"
    ? `подтверждено, ${m.observations} набл.`
    : m.status === "suspected"
      ? `подозрение, ${m.observations} из 2`
      : m.status === "resolved"
        ? "исправлено, следим"
        : "оспорено — не учитываем";
