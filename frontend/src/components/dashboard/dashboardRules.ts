// Dashboard rules (front-end demo). Saved programs are the input: their requirements are merged
// into one list of exams, checked against real-world dates and rounds, and mirrored into
// "Подготовка". Pure functions, no React.

import type { Profile } from "../choice/assistant";
import type { IconName } from "../choice/Icon";
import { evaluate, formatEur, LEVEL_LABEL, programById, type Level, type Program } from "../choice/programs";
import {
  dateKey,
  daysBetween,
  examMilestoneId,
  formatDate,
  parseDeadline,
  plannedTest,
  registrationBy,
  TEST_DATES,
  TODAY,
  type TestDates,
} from "../prep/prepData";

export type DashTab = "overview" | "exams" | "calendar" | "programs";

export const DASH_TABS: { tab: DashTab; label: string; icon: IconName }[] = [
  { tab: "overview", label: "Главное", icon: "layout-dashboard" },
  { tab: "exams", label: "Экзамены", icon: "book-open-check" },
  { tab: "calendar", label: "Календарь", icon: "calendar-days" },
  { tab: "programs", label: "Программы", icon: "graduation-cap" },
];

/* ---------- Exam calendar (demo) ---------- */

export type ExamId = "sat" | "ielts" | "ent";

type ExamSpec = {
  id: ExamId;
  name: string;
  unit: string;
  /** Days between the test and the result the university can see */
  resultLag: number;
  dates: Date[];
};

export const EXAMS: Record<ExamId, ExamSpec> = {
  sat: { id: "sat", name: "SAT Math", unit: "из 800", resultLag: 13, dates: TEST_DATES.sat },
  ielts: { id: "ielts", name: "IELTS Academic", unit: "из 9.0", resultLag: 13, dates: TEST_DATES.ielts },
  ent: { id: "ent", name: "ЕНТ · математика", unit: "из 50", resultLag: 1, dates: TEST_DATES.ent },
};

/* ---------- 1. Union engine ---------- */

export type Demand = { program: Program; threshold: number; enough: boolean; note: string };

export type UnionExam = {
  exam: ExamSpec;
  /** The highest bar among the saved programs */
  target: number;
  targetOwner: Program;
  demands: Demand[];
};

const fmt = (id: ExamId, value: number) => (id === "ielts" ? value.toFixed(1) : String(value));

/** Requirements of all saved programs merged: one exam per kind, the target is the highest bar. */
export function unionExams(programs: Program[]): UnionExam[] {
  const result: UnionExam[] = [];

  const add = (id: ExamId, need: { program: Program; threshold: number }[]) => {
    if (!need.length) return;
    const target = Math.max(...need.map((n) => n.threshold));
    const targetOwner = need.find((n) => n.threshold === target)!.program;
    result.push({
      exam: EXAMS[id],
      target,
      targetOwner,
      demands: need
        .map(({ program, threshold }) => ({
          program,
          threshold,
          enough: threshold >= target,
          note:
            threshold >= target
              ? `${fmt(id, threshold)} — самая высокая планка`
              : `${fmt(id, threshold)} хватает сюда, но ради ${targetOwner.university} тянем до ${fmt(id, target)}`,
        }))
        .sort((a, b) => b.threshold - a.threshold),
    });
  };

  // SAT thresholds in the dataset are for the whole test; the Math section target is half
  add(
    "sat",
    programs.filter((p) => p.satMin).map((p) => ({ program: p, threshold: Math.round(p.satMin! / 2 / 10) * 10 }))
  );
  add(
    "ielts",
    programs.filter((p) => p.englishTaught).map((p) => ({ program: p, threshold: p.ieltsMin }))
  );
  add(
    "ent",
    programs.filter((p) => p.country === "Казахстан").map((p) => ({ program: p, threshold: 40 }))
  );

  return result;
}

export const examLabel = (u: UnionExam) => `${u.exam.name} · ${fmt(u.exam.id, u.target)} ${u.exam.unit}`;

/* ---------- 2. Hard conflicts ---------- */

export type Conflict = {
  id: string;
  kind: "late-result" | "rounds" | "deadline-pile";
  text: string;
  options: string[];
};

/** Real-world checks a student usually finds out about too late. */
export function hardConflicts(programs: Program[], exams: UnionExam[], chosen?: TestDates): Conflict[] {
  const list: Conflict[] = [];

  // The test result has to reach the university before its deadline
  for (const { exam } of exams) {
    for (const program of programs) {
      const needs =
        (exam.id === "sat" && program.satMin) ||
        (exam.id === "ielts" && program.englishTaught) ||
        (exam.id === "ent" && program.country === "Казахстан");
      if (!needs) continue;

      const deadline = parseDeadline(program.deadline);
      const planned = plannedTest(exam.id, chosen);
      if (!planned) continue;
      const results = new Date(planned.getTime() + exam.resultLag * 86_400_000);
      if (results <= deadline) continue;

      const earlier = exam.dates.find((d) => d > TODAY && new Date(d.getTime() + exam.resultLag * 86_400_000) <= deadline);
      list.push({
        id: `late-${exam.id}-${program.id}`,
        kind: "late-result",
        text: `${exam.name} ${formatDate(planned)}: результат придёт к ${formatDate(results)}, а подача в ${program.university} закрывается ${formatDate(deadline)}`,
        options: earlier
          ? [`Сдавать ${formatDate(earlier)}`, `Подать в ${program.university} следующей волной`]
          : [`Убрать ${program.university} из ранней подачи`, "Искать более ранний слот теста"],
      });
    }
  }

  // Mutually exclusive application rounds
  const single = programs.find((p) => p.round === "single-choice-early");
  const otherEarly = programs.find((p) => p.round && p.round !== "regular" && p.id !== single?.id);
  if (single && otherEarly) {
    list.push({
      id: "rounds",
      kind: "rounds",
      text: `${single.university} принимает по Single-Choice Early, а ${otherEarly.university} — по Early Decision. Одновременно подать нельзя`,
      options: [`Ранняя подача только в ${single.university}`, `Ранняя подача только в ${otherEarly.university}`, "Обе — обычной волной"],
    });
  }

  // Two big packages on the same days
  const byDate = [...programs].sort((a, b) => parseDeadline(a.deadline).getTime() - parseDeadline(b.deadline).getTime());
  for (let i = 1; i < byDate.length; i++) {
    const gap = daysBetween(parseDeadline(byDate[i - 1].deadline), parseDeadline(byDate[i].deadline));
    if (gap <= 3) {
      list.push({
        id: `pile-${byDate[i - 1].id}-${byDate[i].id}`,
        kind: "deadline-pile",
        text: `Подачи в ${byDate[i - 1].university} и ${byDate[i].university} почти в один день — ${byDate[i - 1].deadline} и ${byDate[i].deadline}`,
        options: ["Собрать документы на неделю раньше", "Оставить как есть — я успею"],
      });
    }
  }

  return list;
}

/* ---------- 3–4. What preparation gets, and what happens if a program leaves ---------- */

export type Milestone = {
  date: Date;
  title: string;
  detail: string;
  /** The milestone a student ticks done for this date; IELTS has none — it is not planned */
  milestone?: string;
  /** Another sitting of a planned exam: not in the plan, the student may pick it instead */
  alternative?: { exam: "sat" | "ent"; key: string };
};

/**
 * Registration and application dates the section fills by itself, for the sitting the student picked.
 * With `alternatives` the other sittings of SAT and ЕНТ are listed too, so one can be picked in the calendar.
 */
export function calendar(programs: Program[], exams: UnionExam[], chosen?: TestDates, alternatives = false): Milestone[] {
  const list: Milestone[] = [];
  for (const { exam } of exams) {
    const planned = plannedTest(exam.id, chosen);
    if (!planned) continue;
    const dated = exam.id === "ielts" ? null : exam.id;
    list.push({
      date: registrationBy(planned),
      title: `Регистрация на ${exam.name}`,
      detail: `за месяц до теста ${formatDate(planned)}`,
      milestone: dated ? examMilestoneId(dated, "reg", planned) : undefined,
    });
    list.push({
      date: planned,
      title: exam.name,
      detail: dated ? "тест · твоя дата" : "тест",
      milestone: dated ? examMilestoneId(dated, "test", planned) : undefined,
    });
    if (alternatives && dated) {
      for (const other of exam.dates.filter((d) => d > TODAY && d.getTime() !== planned.getTime())) {
        list.push({
          date: other,
          title: exam.name,
          detail: `другая дата · сейчас выбрано ${formatDate(planned)}`,
          alternative: { exam: dated, key: dateKey(other) },
        });
      }
    }
  }
  for (const p of programs) {
    list.push({ date: parseDeadline(p.deadline), title: `Подача · ${p.university}`, detail: p.program, milestone: `apply-${p.id}` });
  }
  return list.sort((a, b) => a.date.getTime() - b.date.getTime());
}

export type RemovalEffect = { program: Program; drops: string[]; stays: string[] };

/** What would leave preparation if this program went away — and what is kept anyway. */
export function removalEffects(programs: Program[], exams: UnionExam[]): RemovalEffect[] {
  return programs.map((program) => {
    const drops: string[] = [];
    const stays: string[] = [];
    for (const union of exams) {
      const others = union.demands.filter((d) => d.program.id !== program.id);
      const mine = union.demands.find((d) => d.program.id === program.id);
      if (!mine) continue;
      if (!others.length) drops.push(union.exam.name);
      else {
        const newTarget = Math.max(...others.map((d) => d.threshold));
        stays.push(
          newTarget < union.target
            ? `${union.exam.name}: цель опустится с ${fmt(union.exam.id, union.target)} до ${fmt(union.exam.id, newTarget)}`
            : `${union.exam.name}: цель не изменится`
        );
      }
    }
    return { program, drops, stays };
  });
}

/* ---------- 5. Programs that no longer fit the profile ---------- */

export type Watch = {
  program: Program;
  level: Level;
  levelLabel: string;
  reason: string;
};

/** A changed profile never deletes a saved program — it only raises a flag. */
export function watchList(programs: Program[], profile: Profile): Watch[] {
  const budget = profile.budget?.match(/(\d[\d\s]*)/);
  const limit = budget ? Number(budget[1].replace(/\s/g, "")) : undefined;

  return programs.flatMap((program) => {
    const { level } = evaluate(program, profile);
    if (limit !== undefined && program.costEur > limit) {
      return [
        {
          program,
          level,
          levelLabel: LEVEL_LABEL[level],
          reason: `${formatEur(program.costEur)} больше твоего бюджета (${profile.budget})`,
        },
      ];
    }
    if (level === "unlikely") {
      return [{ program, level, levelLabel: LEVEL_LABEL[level], reason: "по нынешнему профилю программа стала маловероятной" }];
    }
    return [];
  });
}

export { programById };

/* ---------- Month calendar ---------- */

export type CalendarKind = "registration" | "test" | "application";

export type CalendarEvent = Milestone & { kind: CalendarKind; id: string };

const kindOf = (title: string): CalendarKind =>
  title.startsWith("Регистрация") ? "registration" : title.startsWith("Подача") ? "application" : "test";

/** The same dates, tagged so the calendar can colour them. */
export function calendarEvents(programs: Program[], exams: UnionExam[], chosen?: TestDates, alternatives = false): CalendarEvent[] {
  return calendar(programs, exams, chosen, alternatives).map((m, i) => ({ ...m, id: `${i}-${m.title}`, kind: kindOf(m.title) }));
}

export const sameDay = (a: Date, b: Date) =>
  a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();

/** Six weeks of cells, Monday first, so the grid never jumps in height. */
export function monthGrid(year: number, month: number): Date[] {
  const first = new Date(year, month, 1);
  const start = new Date(first);
  start.setDate(1 - ((first.getDay() + 6) % 7));
  return Array.from({ length: 42 }, (_, i) => new Date(start.getFullYear(), start.getMonth(), start.getDate() + i));
}

/* ---------- Activity ---------- */

export type ActivityDay = { date: Date; count: number; level: 0 | 1 | 2 | 3; parts: string[] };

/** What the student actually did, by day: tasks and mocks from preparation plus chats. */
export function activityByDay(
  evidence: { source: string; date: Date }[],
  chatDays: number[],
  weeks = 5
): ActivityDay[] {
  const counts = new Map<string, { count: number; parts: Map<string, number> }>();
  const key = (d: Date) => `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;

  const bump = (date: Date, what: string) => {
    const k = key(date);
    const entry = counts.get(k) ?? { count: 0, parts: new Map() };
    entry.count += 1;
    entry.parts.set(what, (entry.parts.get(what) ?? 0) + 1);
    counts.set(k, entry);
  };

  for (const e of evidence) bump(e.date, e.source === "чат" ? "разговор" : e.source === "мок" ? "мок" : "задача");
  for (const ts of chatDays) bump(new Date(ts), "разговор");

  // Start on a Monday, so a column of the grid is exactly one week
  const start = new Date(TODAY.getFullYear(), TODAY.getMonth(), TODAY.getDate() - (weeks * 7 - 1));
  start.setDate(start.getDate() - ((start.getDay() + 6) % 7));
  const days = daysBetween(start, TODAY) + 1;

  return Array.from({ length: days }, (_, i) => {
    const date = new Date(start.getFullYear(), start.getMonth(), start.getDate() + i);
    const entry = counts.get(key(date));
    const count = entry?.count ?? 0;
    return {
      date,
      count,
      level: count === 0 ? 0 : count === 1 ? 1 : count <= 3 ? 2 : 3,
      parts: entry ? [...entry.parts].map(([what, n]) => `${what}: ${n}`) : [],
    } as ActivityDay;
  });
}

/** Days in a row up to today. */
export function streak(days: ActivityDay[]): number {
  let n = 0;
  for (let i = days.length - 1; i >= 0; i--) {
    if (days[i].count === 0) break;
    n++;
  }
  return n;
}
