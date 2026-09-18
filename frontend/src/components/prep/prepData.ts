// "Подготовка" (product-logic §4) — demo data and the deterministic rules the screens need.
// Everything here stands in for the backend: requirements come from saved programs, the rest
// (skill map, sets, forecast, milestones) is a fixed demo scenario flagged as "демо" in the UI.

import { PROGRAMS, programById, type Program } from "../choice/programs";

/* ---------- Dates ---------- */

const DEMO_SHIFT_KEY = "quack-demo-shift";

/**
 * Demo only: days the clock was moved forward from the account menu, to watch deadlines come and pass.
 * Read once on load; the server always renders day zero, and nothing dated renders before the workspace loads.
 */
export const DEMO_SHIFT = (() => {
  if (typeof window === "undefined") return 0;
  try {
    return Math.max(0, Number(localStorage.getItem(DEMO_SHIFT_KEY)) || 0);
  } catch {
    return 0;
  }
})();

// The demo "today"; all timelines are laid out around it
export const TODAY = new Date(2026, 8, 17 + DEMO_SHIFT);

/** Moves the demo clock (null puts it back) and reloads, so every screen reads the same day. */
export function shiftDemoClock(days: number | null, cause?: string) {
  try {
    if (days === null) localStorage.removeItem(DEMO_SHIFT_KEY);
    else localStorage.setItem(DEMO_SHIFT_KEY, String(DEMO_SHIFT + days));
    if (cause) localStorage.setItem("quack-pending-cause", JSON.stringify(cause));
  } catch {}
  window.location.reload();
}

export const day = (month: number, date: number, year = 2026) => new Date(year, month - 1, date);

const MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"];
const MONTHS_SHORT = ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"];

export const formatDate = (d: Date) => `${d.getDate()} ${MONTHS[d.getMonth()]}`;
export const formatShort = (d: Date) => `${d.getDate()} ${MONTHS_SHORT[d.getMonth()]}`;
export const daysBetween = (a: Date, b: Date) => Math.round((b.getTime() - a.getTime()) / 86_400_000);

/** Program deadlines are stored as "15 декабря"; the next occurrence after today. */
export function parseDeadline(text: string): Date {
  const [n, month] = text.split(" ");
  const d = new Date(TODAY.getFullYear(), MONTHS.indexOf(month), Number(n));
  if (d < TODAY) d.setFullYear(d.getFullYear() + 1);
  return d;
}

/* ---------- Skill map (§5.2) ---------- */

/** State words from memory-architecture: closed/solid, shaky, prerequisite not held, low data. */
export type SkillState = "solid" | "shaky" | "weak" | "lowData";

export const STATE_LABEL: Record<SkillState, string> = {
  solid: "твёрдо",
  shaky: "шатко",
  weak: "не держится",
  lowData: "мало данных",
};

export type MisconceptionStatus = "suspected" | "confirmed" | "resolved" | "disputed";

export type Misconception = {
  id: string;
  text: string;
  status: MisconceptionStatus;
  observations: number;
  /** When it tends to show up */
  trigger?: string;
};

export type Evidence = { source: "мок" | "замер" | "задача" | "чат"; text: string; date: Date };

export type Skill = {
  id: string;
  name: string;
  area: string;
  /** Share of the exam score, % */
  weight: number;
  state: SkillState;
  /** Probability of recall now, 0–1 (shown as a bar) */
  recall: number;
  requires: string[];
  /** A prerequisite the student's errors trace back to */
  root?: boolean;
  misconceptions: Misconception[];
  evidence: Evidence[];
};

export const AREAS = ["Алгебра", "Продвинутая математика", "Анализ данных", "Геометрия и тригонометрия"];

export const SKILLS: Skill[] = [
  {
    id: "linear",
    name: "Линейные уравнения",
    area: "Алгебра",
    weight: 9,
    state: "solid",
    recall: 0.92,
    requires: [],
    misconceptions: [],
    evidence: [
      { source: "замер", text: "4 из 4 верно, в среднем 48 секунд", date: day(9, 3) },
      { source: "мок", text: "Мок по сету 1: 3 из 3", date: day(9, 12) },
    ],
  },
  {
    id: "systems",
    name: "Системы уравнений",
    area: "Алгебра",
    weight: 8,
    state: "solid",
    recall: 0.86,
    requires: ["linear"],
    misconceptions: [],
    evidence: [{ source: "мок", text: "Мок по сету 1: 2 из 2", date: day(9, 12) }],
  },
  {
    id: "abs",
    name: "Модуль и его раскрытие",
    area: "Алгебра",
    weight: 6,
    state: "weak",
    recall: 0.38,
    requires: ["linear"],
    misconceptions: [
      {
        id: "abs-branch",
        text: "Теряет вторую ветвь при |x − a|",
        status: "confirmed",
        observations: 3,
        trigger: "при отрицательной ветви и когда торопится",
      },
    ],
    evidence: [
      { source: "замер", text: "Задача 7: ответ 3 вместо «3 и −3» — ловушка «вторая ветвь»", date: day(9, 3) },
      { source: "задача", text: "|2x − 1| = 5: только x = 3", date: day(9, 14) },
      { source: "чат", text: "«модуль же всегда положительный, значит один ответ»", date: day(9, 15) },
    ],
  },
  {
    id: "inequalities",
    name: "Неравенства",
    area: "Алгебра",
    weight: 7,
    state: "shaky",
    recall: 0.55,
    requires: ["linear", "abs"],
    misconceptions: [],
    evidence: [{ source: "замер", text: "1 из 2: ошибка знака при делении на отрицательное", date: day(9, 3) }],
  },
  {
    id: "quadratics",
    name: "Квадратичные функции",
    area: "Продвинутая математика",
    weight: 11,
    state: "solid",
    recall: 0.84,
    requires: ["linear"],
    misconceptions: [
      { id: "quad-sign", text: "Знак при раскрытии скобок перед минусом", status: "resolved", observations: 2 },
    ],
    evidence: [
      { source: "замер", text: "Задача 3: ловушка «знак перед скобкой»", date: day(9, 3) },
      { source: "мок", text: "Мок по сету 1: 4 из 4, ловушку обошёл", date: day(9, 12) },
    ],
  },
  {
    id: "polynomials",
    name: "Многочлены и корни",
    area: "Продвинутая математика",
    weight: 8,
    state: "shaky",
    recall: 0.5,
    requires: ["quadratics"],
    misconceptions: [],
    evidence: [{ source: "задача", text: "2 из 3: теорема Виета — верно, деление — ошибка", date: day(9, 10) }],
  },
  {
    id: "exponential",
    name: "Показательные функции",
    area: "Продвинутая математика",
    weight: 7,
    state: "lowData",
    recall: 0.6,
    requires: ["quadratics"],
    misconceptions: [],
    evidence: [{ source: "чат", text: "Спрашивал, чем рост отличается от линейного", date: day(9, 8) }],
  },
  {
    id: "ratios",
    name: "Проценты и пропорции",
    area: "Анализ данных",
    weight: 6,
    state: "solid",
    recall: 0.9,
    requires: [],
    misconceptions: [],
    evidence: [{ source: "замер", text: "3 из 3", date: day(9, 3) }],
  },
  {
    id: "statistics",
    name: "Среднее и разброс",
    area: "Анализ данных",
    weight: 5,
    state: "lowData",
    recall: 0.65,
    requires: ["ratios"],
    misconceptions: [],
    evidence: [{ source: "замер", text: "1 из 1", date: day(9, 3) }],
  },
  {
    id: "probability",
    name: "Вероятность",
    area: "Анализ данных",
    weight: 4,
    state: "lowData",
    recall: 0.5,
    requires: ["ratios"],
    misconceptions: [],
    evidence: [],
  },
  {
    id: "triangles",
    name: "Подобие треугольников",
    area: "Геометрия и тригонометрия",
    weight: 5,
    state: "solid",
    recall: 0.8,
    requires: [],
    misconceptions: [],
    evidence: [{ source: "замер", text: "2 из 2", date: day(9, 3) }],
  },
  {
    id: "circle",
    name: "Свойства окружности",
    area: "Геометрия и тригонометрия",
    weight: 5,
    state: "shaky",
    recall: 0.45,
    requires: ["triangles"],
    root: true,
    misconceptions: [],
    evidence: [
      { source: "замер", text: "Спуск от тригонометрии: вписанный угол — неверно", date: day(9, 3) },
      { source: "задача", text: "Центральный и вписанный угол: верно со второй попытки", date: day(9, 16) },
    ],
  },
  {
    id: "trig",
    name: "Тригонометрия",
    area: "Геометрия и тригонометрия",
    weight: 6,
    state: "weak",
    recall: 0.3,
    requires: ["circle", "triangles"],
    misconceptions: [
      { id: "trig-sincos", text: "Путает sin и cos в прямоугольном треугольнике", status: "suspected", observations: 1 },
    ],
    evidence: [{ source: "замер", text: "0 из 2 — ошибки идут из окружности (корень)", date: day(9, 3) }],
  },
  {
    id: "reduction",
    name: "Формулы приведения",
    area: "Геометрия и тригонометрия",
    weight: 3,
    state: "lowData",
    recall: 0.4,
    requires: ["trig"],
    misconceptions: [],
    evidence: [],
  },
];

export const skillById = (id: string) => SKILLS.find((s) => s.id === id)!;

/* ---------- Sets (§4.3) ---------- */

export type SetStatus = "done" | "current" | "upcoming" | "review";

export const SET_STATUS_LABEL: Record<SetStatus, string> = {
  done: "пройден",
  current: "текущий",
  upcoming: "предстоит",
  review: "закрепление",
};

export type StudySet = {
  id: string;
  number: number;
  title: string;
  /** Area the set is filed under on the Sets tab */
  area: string;
  skills: string[];
  start: Date;
  deadline: Date;
  status: SetStatus;
  why: string;
};

export const SETS: StudySet[] = [
  {
    id: "s1",
    number: 1,
    title: "Квадратичные и системы",
    area: "Продвинутая математика",
    skills: ["quadratics", "systems", "linear"],
    start: day(9, 1),
    deadline: day(9, 12),
    status: "done",
    why: "Самый большой вес в экзамене и фундамент для многочленов",
  },
  {
    id: "s2",
    number: 2,
    title: "Окружность и модуль",
    area: "Геометрия и тригонометрия",
    skills: ["circle", "abs", "triangles"],
    start: day(9, 13),
    deadline: day(10, 1),
    status: "current",
    why: "Окружность — корень ошибок в тригонометрии; модуль — подтверждённая ловушка",
  },
  {
    id: "s3",
    number: 3,
    title: "Неравенства и многочлены",
    area: "Алгебра",
    skills: ["inequalities", "polynomials", "exponential"],
    start: day(10, 2),
    deadline: day(10, 10),
    status: "upcoming",
    why: "Неравенства опираются на модуль, поэтому идут после сета 2",
  },
  {
    id: "s4",
    number: 4,
    title: "Данные и вероятность",
    area: "Анализ данных",
    skills: ["statistics", "probability"],
    start: day(10, 11),
    deadline: day(10, 16),
    status: "upcoming",
    why: "Малый вес, но по навыкам мало данных — короткий сет",
  },
  {
    id: "s5",
    number: 5,
    title: "Тригонометрия",
    area: "Геометрия и тригонометрия",
    skills: ["trig", "reduction"],
    start: day(10, 17),
    deadline: day(10, 23),
    status: "upcoming",
    why: "Строится после окружности; повторяет подобие треугольников",
  },
  {
    id: "s6",
    number: 6,
    title: "Закрепление перед тестом",
    area: "Алгебра",
    skills: ["abs", "quadratics", "trig"],
    start: day(10, 24),
    deadline: day(11, 6),
    status: "review",
    why: "Последний сет перед тестом — без новых навыков, только повторение и полный мок",
  },
];

export const setById = (id: string) => SETS.find((s) => s.id === id)!;

/** A skill is closed for the set when it is solid. */
export const closedCount = (set: StudySet, states: Record<string, SkillState>) =>
  set.skills.filter((id) => states[id] === "solid").length;

/* ---------- Topic guidelines (§4.4) ---------- */

export type Task = {
  id: string;
  text: string;
  options: { label: string; correct?: boolean; trap?: string }[];
  explain: string;
};

export type Guideline = { prepare: string; mustKnow: string[]; traps: string[]; practice: string; tasks: Task[] };

export const GUIDELINES: Record<string, Guideline> = {
  circle: {
    prepare: "Начни с вписанного и центрального угла — на них держится вся тригонометрия дальше. Рисуй чертёж к каждой задаче.",
    mustKnow: ["Вписанный угол равен половине центрального", "Угол, опирающийся на диаметр, — прямой", "Касательная перпендикулярна радиусу"],
    traps: ["Берёшь центральный угол вместо вписанного, когда дуга не подписана"],
    practice: "6–8 задач на углы и дуги, потом мок по топику",
    tasks: [
      {
        id: "c1",
        text: "Центральный угол AOB = 110°. Чему равен вписанный угол ACB, опирающийся на ту же дугу?",
        options: [
          { label: "55°", correct: true },
          { label: "110°", trap: "Взял центральный угол вместо вписанного" },
          { label: "70°" },
          { label: "220°" },
        ],
        explain: "Вписанный угол равен половине центрального, опирающегося на ту же дугу: 110° / 2 = 55°.",
      },
      {
        id: "c2",
        text: "Треугольник вписан в окружность, одна его сторона — диаметр. Какой угол напротив диаметра?",
        options: [{ label: "45°" }, { label: "60°" }, { label: "90°", correct: true }, { label: "Зависит от треугольника", trap: "Не узнал угол, опирающийся на диаметр" }],
        explain: "Угол, опирающийся на диаметр, всегда прямой: он вписанный и опирается на дугу 180°.",
      },
    ],
  },
  abs: {
    prepare: "Раскрывай модуль по определению и всегда проверяй обе ветви — это твоя подтверждённая ловушка.",
    mustKnow: ["|a| = a при a ≥ 0 и −a при a < 0", "|x − a| = b даёт x = a ± b при b ≥ 0", "Уравнение |…| = отрицательное число решений не имеет"],
    traps: ["Теряешь вторую ветвь — чаще при отрицательной ветви и когда торопишься"],
    practice: "Уравнения с модулем, у которых два корня, потом неравенства с модулем",
    tasks: [
      {
        id: "a1",
        text: "Сколько решений у уравнения |2x − 1| = 5?",
        options: [
          { label: "1", trap: "Потерял вторую ветвь" },
          { label: "2", correct: true },
          { label: "0" },
          { label: "Бесконечно много" },
        ],
        explain: "2x − 1 = 5 даёт x = 3, 2x − 1 = −5 даёт x = −2. Два корня.",
      },
    ],
  },
  triangles: {
    prepare: "Навык уже твёрдый — здесь он как повторение перед тригонометрией.",
    mustKnow: ["Признаки подобия", "Отношение площадей — квадрат коэффициента подобия"],
    traps: [],
    practice: "2–3 задачи на повторение",
    tasks: [
      {
        id: "t1",
        text: "Треугольники подобны с коэффициентом 3. Во сколько раз площадь большего больше?",
        options: [{ label: "3", trap: "Взял коэффициент вместо его квадрата" }, { label: "6" }, { label: "9", correct: true }, { label: "27" }],
        explain: "Площади подобных фигур относятся как квадрат коэффициента: 3² = 9.",
      },
    ],
  },
};

/* ---------- Exams and requirements (§4.1) ---------- */

export type Milestone = {
  id: string;
  date: Date;
  title: string;
  detail: string;
  source: string | "демо";
  /** Only milestones can be ticked: they happen outside the product */
  checkable: boolean;
};

export type ExamRequirement = {
  id: "sat" | "ielts" | "ent";
  name: string;
  target: string;
  targetNote: string;
  testDate?: Date;
  testCandidates: Date[];
  programs: Program[];
  /** Exams with a knowledge model get readiness and a forecast; others only milestones */
  hasModel: boolean;
  readiness?: number;
  forecast?: Date;
};

const DEMO_SAVED = ["sapienza", "eth", "valencia"];

/** The saved programs the section works from; the demo set when nothing is saved yet. */
export function savedPrograms(saved: string[], demo: boolean): Program[] {
  const ids = saved.length ? saved : demo ? DEMO_SAVED : [];
  return ids.map(programById).filter(Boolean);
}

/** Requirements are derived from saved programs: the highest threshold wins. */
export function requirements(programs: Program[], forecast: Date, readinessNow: number): ExamRequirement[] {
  const result: ExamRequirement[] = [];

  const satPrograms = programs.filter((p) => p.satMin);
  if (satPrograms.length) {
    const top = Math.max(...satPrograms.map((p) => p.satMin!));
    // SAT total thresholds from the dataset; the Math section target is half, rounded to 10
    const math = Math.round(top / 2 / 10) * 10;
    result.push({
      id: "sat",
      name: "SAT Math",
      target: String(math),
      targetNote: `из 800 · порог ${top} в сумме у ${satPrograms.find((p) => p.satMin === top)!.university}`,
      testDate: day(11, 7),
      testCandidates: [day(11, 7), day(12, 5)],
      programs: satPrograms,
      hasModel: true,
      readiness: readinessNow,
      forecast,
    });
  }

  if (programs.length) {
    const top = Math.max(...programs.map((p) => p.ieltsMin));
    result.push({
      id: "ielts",
      name: "IELTS Academic",
      target: top.toFixed(1),
      targetNote: `нужен всем сохранённым · выше всех у ${programs.find((p) => p.ieltsMin === top)!.university}`,
      testDate: day(12, 12),
      testCandidates: [day(12, 12), day(1, 16, 2027)],
      programs,
      hasModel: false,
    });
  }

  return result;
}

export function milestones(programs: Program[]): Milestone[] {
  const list: Milestone[] = [];
  if (programs.some((p) => p.satMin)) {
    list.push(
      { id: "sat-reg", date: day(10, 10), title: "Регистрация на SAT", detail: "Тест 7 ноября · College Board", source: "демо", checkable: true },
      { id: "sat-test", date: day(11, 7), title: "SAT — тест", detail: "Цель по Math выставлена по сохранённым", source: "демо", checkable: true }
    );
  }
  if (programs.length) {
    list.push(
      { id: "ielts-window", date: day(11, 10), title: "Окно подготовки к IELTS", detail: "10 ноября – 11 декабря · без модели знаний", source: "демо", checkable: false },
      { id: "ielts-test", date: day(12, 12), title: "IELTS — тест", detail: "Ближайший слот в Алматы", source: "демо", checkable: true }
    );
  }
  for (const p of programs) {
    list.push({
      id: `apply-${p.id}`,
      date: parseDeadline(p.deadline),
      title: `Подача · ${p.university}`,
      detail: `${p.program}, ${p.city}`,
      source: "демо",
      checkable: true,
    });
  }
  return list.sort((a, b) => a.date.getTime() - b.date.getTime());
}

/** Conflicts between milestones, each with ways to resolve it. */
export function conflicts(list: Milestone[]): { id: string; text: string; options: string[] }[] {
  const ielts = list.find((m) => m.id === "ielts-test");
  if (!ielts) return [];
  // Results arrive about 13 days after the test
  const results = new Date(ielts.date.getTime() + 13 * 86_400_000);
  return list
    .filter((m) => m.id.startsWith("apply-") && m.date < results)
    .map((m) => ({
      id: `conflict-${m.id}`,
      text: `${m.title} — до ${formatDate(m.date)}, а результат IELTS придёт только к ${formatDate(results)}`,
      options: ["Сдать IELTS раньше — 21 ноября", "Подать без результата и дослать, если программа позволяет"],
    }));
}

/* ---------- Readiness forecast ---------- */

export type ForecastPoint = { date: Date; value: number; kind: "actual" | "forecast" };

/** Readiness history and the forecast to 100%. Higher readiness pulls the forecast in; manual changes push it out. */
export function forecastSeries(now: number, extraDays = 0): { points: ForecastPoint[]; forecast: Date } {
  const history: [Date, number][] = [
    [day(9, 1), 18],
    [day(9, 4), 27],
    [day(9, 8), 33],
    [day(9, 12), 40],
    [day(9, 15), 44],
  ];
  // Each point of readiness above the demo baseline saves about half a day
  const baseline = 54;
  const shift = extraDays - Math.round((now - baseline) * 0.5);
  const forecast = new Date(day(11, 3).getTime() + shift * 86_400_000);
  const span = Math.max(1, daysBetween(TODAY, forecast));
  const future = [0.2, 0.42, 0.62, 0.8, 1].map((t) => {
    const date = new Date(TODAY.getTime() + Math.round(span * t) * 86_400_000);
    // Growth slows towards the end: the last skills are the hardest
    const value = Math.round(now + (100 - now) * (1 - Math.pow(1 - t, 1.6)));
    return [date, value] as [Date, number];
  });
  return {
    forecast,
    points: [
      ...history.filter(([, v]) => v <= now).map(([date, value]) => ({ date, value, kind: "actual" as const })),
      { date: TODAY, value: now, kind: "actual" as const },
      ...future.map(([date, value]) => ({ date, value, kind: "forecast" as const })),
    ],
  };
}

/** Saved programs with their realism: after the diagnostic the SAT part uses the forecast score. */
export function realismShift(programs: Program[]) {
  return programs.map((p) => ({
    program: p,
    basis: p.satMin ? "по прогнозу SAT Math" : "по профилю",
    change:
      p.id === "sapienza"
        ? { from: "стоит попробовать", to: "реалистично", reason: "после замера прогноз SAT Math — 700" }
        : undefined,
  }));
}

export { PROGRAMS };
