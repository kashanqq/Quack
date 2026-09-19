// The backend catalog as the screens know it. `programs.ts` keeps a registry of Program objects and
// of the backend's realism verdicts; this file fills them from /matching and translates the profile
// the student built in the chat into the backend's questionnaire (profile paths).
//
// The backend has no climate, city size, research or exchange data, and no IELTS requirement, so
// those fields stay empty and the screens hide them (Program.remote). Prices are converted to euros
// at rough fixed rates for display only: the catalog is demo data.

import { backend, type BackendMatch, type BackendMatching, type BackendProgram } from "@/api/backend";
import type { Profile } from "./assistant";
import { catalog, formatEur, remoteEvaluations, type Evaluation, type Factor, type Level, type Program } from "./programs";

export const REMOTE = process.env.NEXT_PUBLIC_DATA_SOURCE === "remote";

const EUR_PER: Record<string, number> = { EUR: 1, USD: 0.92, KZT: 0.0017, SGD: 0.68, JPY: 0.006 };

const COUNTRY: Record<string, string> = {
  KZ: "Казахстан",
  DE: "Германия",
  NL: "Нидерланды",
  PL: "Польша",
  FR: "Франция",
  US: "США",
  SG: "Сингапур",
  JP: "Япония",
};
const CITY: Record<string, string> = {
  Almaty: "Алматы",
  Astana: "Астана",
  Shymkent: "Шымкент",
  Karaganda: "Караганда",
  Berlin: "Берлин",
  Munich: "Мюнхен",
  Hamburg: "Гамбург",
  Amsterdam: "Амстердам",
  Delft: "Делфт",
  Warsaw: "Варшава",
  Krakow: "Краков",
  Paris: "Париж",
  Lyon: "Лион",
  Boston: "Бостон",
  Seattle: "Сиэтл",
  Singapore: "Сингапур",
  Tokyo: "Токио",
};
const DIRECTION: Record<string, string> = { Mathematics: "Математика", Engineering: "Инженерия", Economics: "Экономика" };
const MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"];

const LEVEL: Record<BackendMatch["realism"], Level> = { possible: "realistic", try: "try", impossible: "unlikely" };
const STATUS: Record<string, Factor["status"]> = { below: "below", in_range: "ok", above: "ok", unknown: "unknown" };
const EXAM_NAME: Record<string, string> = { SAT_MATH: "SAT (математика)", ENT_MATH: "ЕНТ (математика)" };

/** "2027-05-15" -> "15 мая", the form the deadline parser in prepData understands */
const dayMonth = (iso: string) => {
  const [, m, d] = iso.split("-").map(Number);
  return `${d} ${MONTHS[m - 1]}`;
};

const years = (months: number | null | undefined) => {
  if (!months) return "—";
  const y = Math.round(months / 12);
  return `${y} ${y === 1 ? "год" : y < 5 ? "года" : "лет"}`;
};

/** Hundreds for real sums, tens for the tiny ones (a fictional 5000 yen is €30, not €0) */
const roundCost = (eur: number) => (eur < 1000 ? Math.round(eur / 10) * 10 : Math.round(eur / 100) * 100);

function toProgram(b: BackendProgram): Program {
  const exam = (id: string) => b.requirements.find((r) => r.type === "exam_score" && r.exam_id === id)?.threshold ?? undefined;
  const sat = exam("SAT_MATH");
  const deadline = b.deadlines.filter((d) => d.kind === "application").sort((x, y) => x.date.localeCompare(y.date))[0];
  return {
    id: b.id,
    university: b.university,
    program: DIRECTION[b.direction] ?? b.direction,
    city: CITY[b.city] ?? b.city,
    country: COUNTRY[b.country] ?? b.country,
    region: "europe",
    language: b.language,
    englishTaught: b.language === "English",
    duration: years(b.duration_months),
    costEur: roundCost((b.tuition_per_year ?? 0) * (EUR_PER[b.currency] ?? 1)),
    ieltsMin: 0,
    // Dashboard rules take the math score as satMin / 2 (the frontend thinks in the 1600 total)
    satMin: sat ? sat * 2 : undefined,
    entMin: exam("ENT_MATH"),
    deadline: deadline ? dayMonth(deadline.date) : "—",
    warm: false,
    megacity: false,
    research: "средняя",
    exchange: "",
    remote: true,
  };
}

function factorLabel(id: string) {
  if (id.startsWith("exam_score:")) return EXAM_NAME[id.slice(11)] ?? id.slice(11);
  if (id === "budget") return "Стоимость";
  if (id === "document") return "Документы";
  if (id === "country") return "Страна";
  if (id === "city") return "Город";
  if (id === "direction") return "Направление";
  if (id === "language" || id === "language_pref") return "Язык обучения";
  if (id === "excluded") return "Исключено";
  if (id === "required") return "Обязательное условие";
  if (id.startsWith("deadline")) return "Дедлайн";
  return id;
}

function toEvaluation(m: BackendMatch, program: Program): Evaluation {
  const threshold = (examId: string) => m.program.requirements.find((r) => r.exam_id === examId)?.threshold ?? "?";
  const factors: Factor[] = m.factors.map((f) => ({
    label: factorLabel(f.id),
    value: f.id === "budget" ? formatEur(program.costEur) : f.id.startsWith("exam_score:") ? `от ${threshold(f.id.slice(11))}` : "",
    status: STATUS[f.status] ?? "unknown",
    note: f.text,
  }));
  return {
    level: LEVEL[m.realism],
    factors,
    fits: m.fits_text ? [m.fits_text] : [],
    misfits: [],
    score: m.score,
  };
}

/** Puts a matching answer into the registry; returns the program ids in the backend's order. */
export function ingest(matching: BackendMatching): string[] {
  for (const m of matching.items) {
    const program = toProgram(m.program);
    catalog.set(program.id, program);
    remoteEvaluations.set(program.id, toEvaluation(m, program));
  }
  return matching.items.map((m) => m.program.id);
}

/**
 * The backend ranks by score and treats a stated country or direction as one factor among many, so
 * a cheap program abroad can outrank a fitting one. The picks put what matches the student's country
 * and direction first and keep the backend's order within each group.
 */
export function prioritize(ids: string[]): string[] {
  const misses = (id: string) =>
    (remoteEvaluations.get(id)?.factors ?? []).filter((f) => (f.label === "Страна" || f.label === "Направление") && f.status === "below").length;
  return ids
    .map((id, i) => ({ id, i, m: misses(id) }))
    .sort((a, b) => a.m - b.m || a.i - b.i)
    .map((x) => x.id);
}

/** Loads the whole catalog with the student's realism verdicts; order is the backend's ranking. */
export async function loadCatalog(): Promise<{ ids: string[]; emptyReason: string | null }> {
  const matching = await backend.matching.get(50);
  return { ids: ingest(matching), emptyReason: matching.empty_reason ?? null };
}

/** Ids of the programs the student saved; their data lands in the registry too. */
export async function loadSaved(): Promise<string[]> {
  const page = await backend.saved.list();
  for (const item of page.items) {
    if (!catalog.get(item.program.id)?.remote) catalog.set(item.program.id, toProgram(item.program));
  }
  return page.items.map((i) => i.program_id);
}

/* ---------- Chat profile -> backend questionnaire ---------- */

const REGION_COUNTRIES: Record<string, string[]> = {
  "Южная, Западно-Южная Европа": ["DE", "NL", "PL", "FR"],
  Европа: ["DE", "NL", "PL", "FR"],
  США: ["US"],
  Казахстан: ["KZ"],
  Азия: ["SG", "JP"],
  Канада: ["CA"],
};
const DIRECTION_OUT: Record<string, string> = {
  Бизнес: "Economics",
  Инженерия: "Engineering",
  Медицина: "Medicine",
  "Дизайн и искусство": "Design",
};

const num = (s: string | undefined) => (s && /^\d+(?:\.\d+)?$/.test(s) ? Number(s) : undefined);

/** Dotted questionnaire path -> value, for everything the profile states in a form the backend understands. */
export function profileOps(p: Profile): [string, unknown][] {
  const ops: [string, unknown][] = [];
  const add = (path: string, value: unknown) => {
    if (value !== undefined && value !== "") ops.push([path, value]);
  };

  const grade = p.grade?.match(/\d+/)?.[0];
  add("level.grade", grade ? Number(grade) : undefined);
  add("direction.field", p.direction ? (DIRECTION_OUT[p.direction] ?? p.direction) : undefined);
  add("preferences.countries", p.location ? REGION_COUNTRIES[p.location] : undefined);

  const budget = p.budget?.match(/до\s*(\d+)/);
  if (budget) {
    add("preferences.budget_per_year", Number(budget[1]));
    add("preferences.currency", "EUR");
  }
  const grant = p.grant?.toLowerCase();
  if (grant) add("preferences.grant_need", grant.startsWith("только") ? "only_grant" : grant === "не нужен" ? "not_needed" : "preferred");
  else if (p.budget === "нужен грант") add("preferences.grant_need", "only_grant");

  const sat = num(p.sat);
  add("academics.sat_score", sat === undefined ? undefined : sat > 800 ? Math.round(sat / 2 / 10) * 10 : sat);
  add("academics.ielts_score", num(p.ielts));
  const ent = num(p.ent);
  add("academics.ent_trial_score", ent !== undefined && ent <= 50 ? ent : undefined);
  return ops;
}

let sent = new Map<string, string>();

/** Sends only what changed since the last call; returns whether anything was sent. */
export async function syncProfile(p: Profile): Promise<boolean> {
  const changed = profileOps(p).filter(([path, value]) => sent.get(path) !== JSON.stringify(value));
  for (const [path, value] of changed) {
    await backend.profile.patch(path, value);
    sent.set(path, JSON.stringify(value));
  }
  return changed.length > 0;
}

const FIELD_PATHS: Record<string, string[]> = {
  grade: ["level.grade"],
  direction: ["direction.field"],
  location: ["preferences.countries"],
  budget: ["preferences.budget_per_year", "preferences.currency"],
  grant: ["preferences.grant_need"],
  sat: ["academics.sat_score"],
  ielts: ["academics.ielts_score"],
  ent: ["academics.ent_trial_score"],
};

/**
 * Sends only the given slots. Used for edits in the profile panel: the panel's slots are coarser than
 * the questionnaire (a region instead of countries), so a whole-profile sync would overwrite the agent's data.
 */
export async function syncFields(p: Profile, keys: string[]): Promise<boolean> {
  const paths = new Set(keys.flatMap((k) => FIELD_PATHS[k] ?? []));
  const changed = profileOps(p).filter(([path, value]) => paths.has(path) && sent.get(path) !== JSON.stringify(value));
  for (const [path, value] of changed) {
    await backend.profile.patch(path, value);
    sent.set(path, JSON.stringify(value));
  }
  return changed.length > 0;
}

/** What the server already has, so the next panel edit sends only what it changes */
export const primeSynced = (p: Profile) => {
  sent = new Map(profileOps(p).map(([path, value]) => [path, JSON.stringify(value)]));
};

/** After a reset or sign-out the next student starts from a clean slate */
export const forgetSynced = () => {
  sent = new Map();
};
