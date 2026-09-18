// Where the Подготовка graphs get their data. Until the backend is up this hands out the demo scenario
// from prepData. The graphs only ever see these shapes and lay themselves out from whatever arrives,
// so replacing a stub with a request touches this file alone.
//
// Backend side (backend/ssot/arch-logic.md): the canonical skill map — exam → area → skill with a
// weight and dependencies, 35–45 skills per exam — plus the student's knowledge model on top of it
// (states, recall, evidence, misconceptions), read through get_skill_state. The demo map has 14 skills;
// the layout does not assume that number.

import { AREAS, day, SETS, SKILLS, type Skill, type StudySet } from "./prepData";
import { readStore, writeStore } from "./GraphCanvas";

type Point = { x: number; y: number };

export type SkillMap = {
  /** Areas in the order their lanes are drawn */
  areas: string[];
  skills: Skill[];
};

export type RouteData = {
  exam: string;
  testDate: Date;
  sets: StudySet[];
};

// Built once, so the graphs can memoise their layout on these references
const DEMO_MAP: SkillMap = { areas: AREAS, skills: SKILLS };
const DEMO_ROUTE: RouteData = { exam: "SAT Math", testDate: day(11, 7), sets: SETS };

/** TODO(backend): the canonical map for the student's exam, from the skill-map service. */
export function getSkillMap(): SkillMap {
  return DEMO_MAP;
}

/** TODO(backend): the student's sets and the test date from their requirements. */
export function getRoute(): RouteData {
  return DEMO_ROUTE;
}

const LAYOUT_KEY = "lupidrupi.skillmap.layout.v2";

/**
 * Where the student has dragged skills to — only the moved ones, so skills the backend adds later
 * still get an automatic place. TODO(backend): keep this with the student, so the arrangement follows
 * them to another device; pan and zoom stay per-device in GraphCanvas.
 */
export function loadMapLayout(): Record<string, Point> {
  return readStore<Record<string, Point>>(LAYOUT_KEY) ?? {};
}

export function saveMapLayout(moved: Record<string, Point>) {
  writeStore(LAYOUT_KEY, Object.keys(moved).length ? moved : null);
}
