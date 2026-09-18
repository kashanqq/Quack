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

/** First day of every month the span touches: the ticks on routes and charts. */
export function monthStarts(from: Date, to: Date): Date[] {
  const list: Date[] = [];
  const d = new Date(from.getFullYear(), from.getMonth(), 1);
  if (d < from) d.setMonth(d.getMonth() + 1);
  for (; d <= to; d.setMonth(d.getMonth() + 1)) list.push(new Date(d));
  return list;
}

/* ---------- Exams with a knowledge model ---------- */

/**
 * Every exam the section prepares for has its own skills, sets, readiness and forecast. The screens
 * show one exam at a time and switch between them, so the map never mixes maths with English.
 */
export type ExamId = "sat" | "ielts";

export const EXAM_IDS: ExamId[] = ["sat", "ielts"];

export const EXAMS: Record<ExamId, { name: string; test: Date; routeFrom: Date; routeTo: Date }> = {
  sat: { name: "SAT Math", test: day(11, 7), routeFrom: day(9, 1), routeTo: day(11, 12) },
  ielts: { name: "IELTS Academic", test: day(12, 12), routeFrom: day(9, 1), routeTo: day(12, 17) },
};

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

export type Evidence = { source: "мок" | "замер" | "задача" | "проверка" | "чат"; text: string; date: Date };

export type Skill = {
  id: string;
  exam: ExamId;
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

/** Areas are the lanes of the map and the groups of the set list, per exam. */
export const AREAS: Record<ExamId, string[]> = {
  sat: ["Алгебра", "Продвинутая математика", "Анализ данных", "Геометрия и тригонометрия"],
  ielts: ["Listening", "Reading", "Writing", "Speaking"],
};

const SAT_SKILLS: Omit<Skill, "exam">[] = [
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

const IELTS_SKILLS: Omit<Skill, "exam">[] = [
  {
    id: "l-detail",
    name: "Детали и формы",
    area: "Listening",
    weight: 12,
    state: "solid",
    recall: 0.82,
    requires: [],
    misconceptions: [],
    evidence: [{ source: "замер", text: "Section 1: 9 из 10, ошибка в написании фамилии", date: day(9, 5) }],
  },
  {
    id: "l-maps",
    name: "Карты и схемы",
    area: "Listening",
    weight: 8,
    state: "shaky",
    recall: 0.5,
    requires: ["l-detail"],
    misconceptions: [],
    evidence: [{ source: "замер", text: "План здания: 3 из 5 — путает «напротив» и «рядом с»", date: day(9, 5) }],
  },
  {
    id: "l-lecture",
    name: "Лекция: главная мысль",
    area: "Listening",
    weight: 10,
    state: "lowData",
    recall: 0.45,
    requires: ["l-detail"],
    misconceptions: [],
    evidence: [],
  },
  {
    id: "r-scan",
    name: "Поиск информации",
    area: "Reading",
    weight: 10,
    state: "solid",
    recall: 0.85,
    requires: [],
    misconceptions: [],
    evidence: [{ source: "замер", text: "Matching information: 6 из 7", date: day(9, 5) }],
  },
  {
    id: "r-tfng",
    name: "True / False / Not Given",
    area: "Reading",
    weight: 12,
    state: "weak",
    recall: 0.35,
    requires: ["r-scan"],
    misconceptions: [
      {
        id: "tfng-false",
        text: "Ставит False, когда в тексте ответа просто нет",
        status: "confirmed",
        observations: 3,
        trigger: "когда утверждение звучит правдоподобно",
      },
    ],
    evidence: [
      { source: "замер", text: "TFNG: 2 из 6, все ошибки — False вместо Not Given", date: day(9, 5) },
      { source: "чат", text: "«если в тексте этого нет, значит неправда»", date: day(9, 11) },
    ],
  },
  {
    id: "r-headings",
    name: "Заголовки абзацев",
    area: "Reading",
    weight: 8,
    state: "shaky",
    recall: 0.5,
    requires: ["r-scan"],
    misconceptions: [],
    evidence: [{ source: "замер", text: "3 из 5: выбирает заголовок по совпавшему слову", date: day(9, 5) }],
  },
  {
    id: "w-task1",
    name: "Task 1: описание графика",
    area: "Writing",
    weight: 12,
    state: "shaky",
    recall: 0.5,
    requires: [],
    misconceptions: [],
    evidence: [{ source: "замер", text: "Черновик без обзора (overview) — потолок 5.5 по Task Achievement", date: day(9, 6) }],
  },
  {
    id: "w-coherence",
    name: "Связность и связки",
    area: "Writing",
    weight: 6,
    state: "shaky",
    recall: 0.48,
    requires: [],
    root: true,
    misconceptions: [],
    evidence: [{ source: "замер", text: "Абзацы без главной мысли, связки подряд: moreover, furthermore", date: day(9, 6) }],
  },
  {
    id: "w-task2",
    name: "Task 2: эссе",
    area: "Writing",
    weight: 16,
    state: "weak",
    recall: 0.3,
    requires: ["w-coherence"],
    misconceptions: [],
    evidence: [{ source: "замер", text: "Эссе на 5.0: мысль теряется ко второму абзацу — идёт от связности", date: day(9, 6) }],
  },
  {
    id: "s-part1",
    name: "Part 1: короткие ответы",
    area: "Speaking",
    weight: 6,
    state: "solid",
    recall: 0.88,
    requires: [],
    misconceptions: [],
    evidence: [{ source: "замер", text: "Отвечает развёрнуто, без пауз", date: day(9, 7) }],
  },
  {
    id: "s-part2",
    name: "Part 2: монолог 2 минуты",
    area: "Speaking",
    weight: 10,
    state: "lowData",
    recall: 0.4,
    requires: ["s-part1"],
    misconceptions: [],
    evidence: [],
  },
];

export const SKILLS: Skill[] = [
  ...SAT_SKILLS.map((s) => ({ ...s, exam: "sat" as const })),
  ...IELTS_SKILLS.map((s) => ({ ...s, exam: "ielts" as const })),
];

export const skillById = (id: string) => SKILLS.find((s) => s.id === id)!;

/* ---------- Sets (§4.3) ---------- */

export type SetStatus = "done" | "current" | "upcoming" | "review";

export const SET_STATUS_LABEL: Record<SetStatus, string> = {
  done: "пройден",
  current: "текущий",
  upcoming: "не начат",
  review: "закрепление",
};

export type StudySet = {
  id: string;
  exam: ExamId;
  /** Counted within its exam: SAT and IELTS each start from set 1 */
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

const SAT_SETS: Omit<StudySet, "exam">[] = [
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

/* IELTS runs alongside SAT: its sets overlap the maths ones in time and end before the December test. */
const IELTS_SETS: Omit<StudySet, "exam">[] = [
  {
    id: "i1",
    number: 1,
    title: "Reading: TFNG и заголовки",
    area: "Reading",
    skills: ["r-scan", "r-tfng", "r-headings"],
    start: day(9, 21),
    deadline: day(10, 12),
    status: "upcoming",
    why: "True / False / Not Given — подтверждённая ловушка и самый большой вес в Reading",
  },
  {
    id: "i2",
    number: 2,
    title: "Writing: связность и эссе",
    area: "Writing",
    skills: ["w-coherence", "w-task2"],
    start: day(10, 13),
    deadline: day(11, 2),
    status: "upcoming",
    why: "Связность — корень: из-за неё эссе не поднимается выше 5.5",
  },
  {
    id: "i3",
    number: 3,
    title: "Listening: карты и лекции",
    area: "Listening",
    skills: ["l-detail", "l-maps", "l-lecture"],
    start: day(11, 3),
    deadline: day(11, 17),
    status: "upcoming",
    why: "Детали уже держатся — на них строятся карты и лекция",
  },
  {
    id: "i4",
    number: 4,
    title: "Task 1 и монолог",
    area: "Speaking",
    skills: ["w-task1", "s-part1", "s-part2"],
    start: day(11, 18),
    deadline: day(11, 29),
    status: "upcoming",
    why: "Оба про описание: график на письме и тема на две минуты вслух",
  },
  {
    id: "i5",
    number: 5,
    title: "Пробный IELTS целиком",
    area: "Reading",
    skills: ["r-tfng", "w-task2", "s-part2"],
    start: day(11, 30),
    deadline: day(12, 7),
    status: "review",
    why: "Последняя неделя — без новых навыков, полный тест на время",
  },
];

export const SETS: StudySet[] = [
  ...SAT_SETS.map((s) => ({ ...s, exam: "sat" as const })),
  ...IELTS_SETS.map((s) => ({ ...s, exam: "ielts" as const })),
];

export const setById = (id: string) => SETS.find((s) => s.id === id)!;

/** A skill is closed for the set when it is solid. */
export const closedCount = (set: StudySet, states: Record<string, SkillState>) =>
  set.skills.filter((id) => states[id] === "solid").length;

/* ---------- «Проверь себя» (§4.4) ---------- */

/**
 * Short questions that prove a skill rather than teach it: each answer is evidence for the knowledge
 * model, and the skill's node on the map turns green or yellow with it. A trap option names the
 * misconception it reveals.
 */
export type Task = {
  id: string;
  text: string;
  options: { label: string; correct?: boolean; trap?: string }[];
};

export const CHECKS: Record<string, Task[]> = {
  circle: [
    {
      id: "c1",
      text: "Центральный угол AOB = 110°. Чему равен вписанный угол ACB, опирающийся на ту же дугу?",
      options: [
        { label: "55°", correct: true },
        { label: "110°", trap: "Взял центральный угол вместо вписанного" },
        { label: "70°" },
        { label: "220°" },
      ],
    },
    {
      id: "c2",
      text: "Треугольник вписан в окружность, одна его сторона — диаметр. Какой угол напротив диаметра?",
      options: [{ label: "45°" }, { label: "60°" }, { label: "90°", correct: true }, { label: "Зависит от треугольника", trap: "Не узнал угол, опирающийся на диаметр" }],
    },
  ],
  abs: [
    {
      id: "a1",
      text: "Сколько решений у уравнения |2x − 1| = 5?",
      options: [{ label: "1", trap: "Потерял вторую ветвь" }, { label: "2", correct: true }, { label: "0" }, { label: "Бесконечно много" }],
    },
  ],
  triangles: [
    {
      id: "t1",
      text: "Треугольники подобны с коэффициентом 3. Во сколько раз площадь большего больше?",
      options: [{ label: "3", trap: "Взял коэффициент вместо его квадрата" }, { label: "6" }, { label: "9", correct: true }, { label: "27" }],
    },
  ],
  "r-scan": [
    {
      id: "rs1",
      text: "Текст: «The museum, founded in 1872, moved to its current building in 1905». Когда музей переехал?",
      options: [{ label: "1872", trap: "Взял первую дату, не дочитав предложение" }, { label: "1905", correct: true }, { label: "Не сказано" }],
    },
  ],
  "r-tfng": [
    {
      id: "tf1",
      text: "Текст: «Most visitors arrive by train». Утверждение: «The museum is free to visit». Ответ?",
      options: [
        { label: "True" },
        { label: "False", trap: "False вместо Not Given: в тексте этого нет" },
        { label: "Not Given", correct: true },
      ],
    },
    {
      id: "tf2",
      text: "Текст: «The bridge was completed two years behind schedule». Утверждение: «The bridge was finished on time». Ответ?",
      options: [{ label: "True" }, { label: "False", correct: true }, { label: "Not Given", trap: "Not Given, хотя текст прямо противоречит" }],
    },
  ],
  "r-headings": [
    {
      id: "rh1",
      text: "Абзац о том, почему города сажают деревья: тень, воздух, дешевле кондиционеров. Лучший заголовок?",
      options: [
        { label: "The history of city parks", trap: "Выбрал заголовок по совпавшему слову, а не по мысли" },
        { label: "Practical benefits of urban trees", correct: true },
        { label: "How air conditioners work" },
      ],
    },
  ],
  "w-coherence": [
    {
      id: "wc1",
      text: "Какая связка подходит: «Prices rose sharply. ___, demand stayed the same»?",
      options: [{ label: "Moreover", trap: "Связка добавления там, где нужен контраст" }, { label: "However", correct: true }, { label: "Therefore" }],
    },
  ],
  "w-task2": [
    {
      id: "wt1",
      text: "Тема: «Some think students should study abroad». С чего по критериям лучше начать эссе?",
      options: [
        { label: "С истории образования за границей", trap: "Вступление уходит от вопроса" },
        { label: "Перефразировать тему и сразу дать свою позицию", correct: true },
        { label: "С цитаты известного человека" },
      ],
    },
  ],
  "w-task1": [
    {
      id: "w1",
      text: "Что обязательно должно быть в Task 1, чтобы подняться выше 5.5?",
      options: [{ label: "Все числа с графика" }, { label: "Обзор главных тенденций (overview)", correct: true }, { label: "Своё мнение", trap: "Мнение в Task 1 не нужно" }],
    },
  ],
  "l-maps": [
    {
      id: "lm1",
      text: "На записи: «The café is opposite the library». Где кафе на плане?",
      options: [{ label: "Рядом с библиотекой, стена к стене", trap: "Путает «opposite» и «next to»" }, { label: "Через проход, лицом к библиотеке", correct: true }, { label: "За библиотекой" }],
    },
  ],
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

/** Readiness now and its forecast, per exam with a knowledge model. */
export type ExamOutlook = Record<ExamId, { readiness: number; forecast: Date }>;

/** Requirements are derived from saved programs: the highest threshold wins. */
export function requirements(programs: Program[], outlook: ExamOutlook): ExamRequirement[] {
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
      testDate: EXAMS.sat.test,
      testCandidates: [EXAMS.sat.test, day(12, 5)],
      programs: satPrograms,
      hasModel: true,
      ...outlook.sat,
    });
  }

  if (programs.length) {
    const top = Math.max(...programs.map((p) => p.ieltsMin));
    result.push({
      id: "ielts",
      name: "IELTS Academic",
      target: top.toFixed(1),
      targetNote: `нужен всем сохранённым · выше всех у ${programs.find((p) => p.ieltsMin === top)!.university}`,
      testDate: EXAMS.ielts.test,
      testCandidates: [EXAMS.ielts.test, day(1, 16, 2027)],
      programs,
      hasModel: true,
      ...outlook.ielts,
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
      { id: "ielts-reg", date: day(11, 12), title: "Регистрация на IELTS", detail: "Тест 12 декабря · British Council", source: "демо", checkable: true },
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

/**
 * The demo history of each exam, the readiness it starts from, and when it would reach 100% from
 * there. IELTS starts later and lower and aims at the December test.
 */
const FORECAST_BASE: Record<ExamId, { history: [Date, number][]; baseline: number; done: Date }> = {
  sat: {
    history: [
      [day(9, 1), 18],
      [day(9, 4), 27],
      [day(9, 8), 33],
      [day(9, 12), 40],
      [day(9, 15), 44],
    ],
    baseline: 54,
    done: day(11, 3),
  },
  ielts: {
    history: [
      [day(9, 5), 24],
      [day(9, 10), 31],
      [day(9, 15), 37],
    ],
    baseline: 41,
    done: day(12, 1),
  },
};

/** Readiness history and the forecast to 100%. Higher readiness pulls the forecast in; manual changes push it out. */
export function forecastSeries(now: number, extraDays = 0, exam: ExamId = "sat"): { points: ForecastPoint[]; forecast: Date } {
  const { history, baseline, done } = FORECAST_BASE[exam];
  // Each point of readiness above the demo baseline saves about half a day
  const shift = extraDays - Math.round((now - baseline) * 0.5);
  const forecast = new Date(done.getTime() + shift * 86_400_000);
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
