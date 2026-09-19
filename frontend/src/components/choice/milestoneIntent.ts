// A milestone or a test date told in the choice chat: «зарегистрировался на SAT», «подал в Болонью»,
// «буду сдавать SAT 5 декабря». The chat ticks and picks the same way the Quack calendar and «Требования»
// do (product-logic §3.2: an action in the chat is a tool call). Keyword rules stand in for the backend's
// assistant. Pure functions, no React.

import {
  dateKey,
  EXAMS,
  examMilestoneId,
  formatDate,
  milestones,
  plannedTest,
  testCandidates,
  type DatedExam,
  type Milestone,
  type TestDates,
} from "../prep/prepData";
import { programById, PROGRAMS } from "./programs";

export type MilestoneIntent =
  /** Done, and one of the student's milestones */
  | { kind: "done"; id: string; title: string }
  /** Only planned: nothing is ticked, the assistant asks */
  | { kind: "planned"; what: string }
  /** Done, but no saved program has such a date */
  | { kind: "unknown"; what: string }
  /** A sitting picked — and, when the message says so, its registration or test ticked as well */
  | { kind: "date"; exam: DatedExam; key: string; test: Date; mark?: { id: string; title: string } }
  /** A date the exam does not sit on: the sittings there are */
  | { kind: "badDate"; exam: DatedExam; options: string[] };

/** Ways the programs are named in a message, beyond the city */
const ALIASES: Record<string, string[]> = {
  valencia: ["valenc", "валенс"],
  sapienza: ["sapienz", "сапиенц", "рим"],
  bologna: ["bologn", "болон"],
  porto: ["porto", "порту"],
  lisbon: ["lisbo", "tecnico", "лиссаб"],
  eth: ["eth", "цюрих", "zurich", "zürich"],
};

const MONTHS = ["январ", "феврал", "март", "апрел", "ма[яй]", "июн", "июл", "август", "сентябр", "октябр", "ноябр", "декабр"];
const MONTH = `(${MONTHS.join("|")})`;

const word = (stem: string) => new RegExp(`(^|[^a-zа-я])${stem}`);

const DONE_REG = /зарегистрировал(ся|ась)|записал(ся|ась) на/;
const DONE_TEST = /(^|[^а-я])сдал(а)?([^а-я]|$)/;
const DONE_APPLY = /(^|[^а-я])(подал(а)?|отправил(а)?)([^а-я]|$)/;
const PLANNED = /собира|планиру|зарегистрир(уюсь|оваться)|запишусь|записаться|подам|подать|сдам|сдать/;
/** «SAT не сдавал» is what the profile hears, not a date: denials are left to it */
const DENIED = /(^|[^а-я])(не|еще не|пока не) (зарегистр|записал|пода|отправ|сда)/;

function examIn(text: string): DatedExam | null {
  if (word("(sat|сат)([^a-zа-я]|$)").test(text)) return "sat";
  if (word("(ент|унт)([^a-zа-я]|$)").test(text)) return "ent";
  return null;
}

function programIn(text: string): string | null {
  for (const p of PROGRAMS) {
    const stems = [...(ALIASES[p.id] ?? []), p.city.toLowerCase().slice(0, 5)];
    if (stems.some((s) => word(s).test(text))) return p.id;
  }
  return null;
}

/** «5 декабря», «14 марта» or just «в декабре»; the text without it, so a day is not read as a score */
function dateIn(text: string): { when: { day?: number; month: number } | null; rest: string } {
  const full = text.match(new RegExp(`(\\d{1,2})\\s*${MONTH}[а-я]*`));
  if (full) {
    const month = MONTHS.findIndex((m) => new RegExp(`^${m}`).test(full[2]));
    return { when: { day: Number(full[1]), month }, rest: text.replace(full[0], " ") };
  }
  const bare = text.match(new RegExp(`(^|[^а-я])(в|на)\\s+${MONTH}[а-я]*`));
  if (bare) {
    const month = MONTHS.findIndex((m) => new RegExp(`^${m}`).test(bare[3]));
    return { when: { month }, rest: text.replace(bare[0], " ") };
  }
  return { when: null, rest: text };
}

/** A milestone in the chat names its sitting: «Регистрация на SAT (тест 5 декабря)», «SAT — тест, 7 ноября» */
const titleOf = (m: Milestone) =>
  !m.test ? m.title : m.id.includes("-reg:") ? `${m.title} (тест ${formatDate(m.test)})` : `${m.title}, ${formatDate(m.test)}`;

/** What the message says about a milestone or a test date, or null when it is about neither. */
export function milestoneIntent(raw: string, saved: string[], chosen: TestDates = {}): MilestoneIntent | null {
  const text = raw.toLowerCase().replace(/ё/g, "е");
  const exam = examIn(text);
  const program = programIn(text);
  const { when, rest } = dateIn(text);
  const programs = saved.map(programById).filter(Boolean);

  // Before anything is saved, talk about exams and applications is the student telling us about themselves
  if (!saved.length || DENIED.test(text)) return null;

  const inPlan = (e: DatedExam) => milestones(programs, chosen).some((m) => m.id.startsWith(`${e}-reg:`));

  // A test date: «буду сдавать SAT 5 декабря», «зарегистрировался на SAT на 5 декабря»
  if (exam && when) {
    if (!inPlan(exam)) return { kind: "unknown", what: `тест ${EXAMS[exam].name}` };
    const sittings = testCandidates(exam);
    const match = sittings.filter((d) => d.getMonth() === when.month && (when.day === undefined || d.getDate() === when.day));
    if (match.length !== 1) return { kind: "badDate", exam, options: sittings.map(formatDate) };
    const test = match[0];
    const key = dateKey(test);
    const tick = DONE_REG.test(text) ? "reg" : DONE_TEST.test(text) ? "test" : null;
    if (!tick) return { kind: "date", exam, key, test };
    const id = examMilestoneId(exam, tick, test);
    const mine = milestones(programs, { ...chosen, [exam]: key }).find((m) => m.id === id);
    return { kind: "date", exam, key, test, mark: { id, title: mine ? titleOf(mine) : id } };
  }

  // «Сдал SAT на 1400» is a score for the profile, not a date
  const planned = exam ? plannedTest(exam, chosen) : undefined;
  const reg = exam && planned && /регистр|запис/.test(text) ? examMilestoneId(exam, "reg", planned) : null;
  const test = exam && planned && !reg && /(^|[^а-я])сда(л|м|ть)/.test(text) && !/\d{2,}/.test(rest) ? examMilestoneId(exam, "test", planned) : null;
  const apply = program && /(^|[^а-я])(пода|отправ)|заявк|документ/.test(text) ? `apply-${program}` : null;
  const id = reg ?? test ?? apply;
  if (!id) return null;

  const what = reg
    ? `регистрацию на ${EXAMS[exam!].name}`
    : test
      ? `тест ${EXAMS[exam!].name}`
      : `подачу в ${programById(program!).university}`;

  if (PLANNED.test(text)) return { kind: "planned", what };
  // Only a past-tense verb ticks: «регистрация на SAT» on its own says nothing about whether it is done
  if (!(DONE_REG.test(text) || DONE_TEST.test(text) || DONE_APPLY.test(text))) return null;

  const mine = milestones(programs, chosen).find((m) => m.id === id);
  if (!mine) return { kind: "unknown", what };
  return { kind: "done", id, title: titleOf(mine) };
}
