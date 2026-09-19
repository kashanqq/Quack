// Simulated assistant for the "Choice" page (front-end only): keyword rules that fill the
// profile, pick the next question and phrase the summary. Pure functions, no React.

/** §3.1 «приоритеты при выборе»: порядок факторов, ученик решает, что важнее — первый в списке весомее. */
export type PriorityKey = "realism" | "cost" | "ranking" | "location" | "program" | "research" | "mobility";

export const PRIORITY_KEYS: PriorityKey[] = ["realism", "cost", "ranking", "location", "program", "research", "mobility"];

export const PRIORITY_LABEL: Record<PriorityKey, string> = {
  realism: "Реалистичность",
  cost: "Стоимость",
  ranking: "Рейтинг вуза",
  location: "Локация",
  program: "Программа/направление",
  research: "Наука",
  mobility: "Мобильность",
};

export type Profile = {
  grade?: string;
  direction?: string;
  location?: string;
  language?: string;
  budget?: string;
  grant?: string;
  sat?: string;
  ielts?: string;
  ent?: string;
  strong?: string;
  soft: string[];
  /** Ограничения (§3.1): что обязательно должно быть и что точно исключено */
  requiredNote?: string;
  excludedNote?: string;
  /** Ранжирование факторов при выборе (§3.1, §3.3); дефолтный порядок = "по умолчанию" */
  priorities: PriorityKey[];
  /** Темп и стиль (§3.1) */
  paceHours?: string;
  paceDepth?: string;
  paceHint?: string;
};

export type FieldKey = Exclude<keyof Profile, "soft" | "priorities"> | "soft" | "priorities";

export const FIELDS: [FieldKey, string][] = [
  ["grade", "Класс"],
  ["direction", "Направление"],
  ["location", "Где учиться"],
  ["language", "Язык обучения"],
  ["budget", "Бюджет"],
  ["grant", "Грант"],
  ["sat", "SAT"],
  ["ielts", "IELTS"],
  ["ent", "ЕНТ"],
  ["strong", "Сильные стороны"],
  ["soft", "Черты и предпочтения"],
  ["requiredNote", "Обязательно"],
  ["excludedNote", "Исключить"],
  ["priorities", "Приоритеты при выборе"],
  ["paceHours", "Часов в неделю"],
  ["paceDepth", "Глубина объяснений"],
  ["paceHint", "Уровень подсказки"],
];

export const EMPTY_PROFILE: Profile = { soft: [], priorities: [...PRIORITY_KEYS] };

/** Backfills fields that did not exist yet when a profile was saved (e.g. in localStorage). */
export function sanitizeProfile(p: Partial<Profile> | null | undefined): Profile {
  return { ...EMPTY_PROFILE, ...p, soft: p?.soft ?? [], priorities: p?.priorities?.length === PRIORITY_KEYS.length ? p.priorities : [...PRIORITY_KEYS] };
}

type MissingKey = "direction" | "location" | "exams" | "budget";

export const QUESTIONS: Record<MissingKey, { ask: string; hint: string }> = {
  direction: {
    ask: "Какое направление тебе ближе — IT, бизнес, медицина или что-то ещё?",
    hint: "Хочу в IT, но интересна и экономика...",
  },
  location: {
    ask: "Где хочешь учиться — Казахстан, Европа, США, Азия?",
    hint: "В Европу, где тепло...",
  },
  exams: {
    ask: "Есть ли результаты экзаменов?",
    hint: "IELTS не сдавал, SAT - 1320...",
  },
  budget: {
    ask: "Какой бюджет в год и нужен ли грант?",
    hint: "До 3000$ в год, грант желательно...",
  },
};

export function fieldValue(profile: Profile, key: FieldKey): string | undefined {
  if (key === "soft") return profile.soft.join(", ") || undefined;
  if (key === "priorities") return profile.priorities.map((k) => PRIORITY_LABEL[k]).join(" › ");
  const value = profile[key];
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : undefined;
}

/** Pull whatever we can recognise out of a message. */
export function extract(current: Profile, raw: string): { profile: Profile; changed: FieldKey[] } {
  const text = raw.toLowerCase().replace(/ё/g, "е");
  const profile: Profile = { ...current, soft: [...current.soft] };
  const changed = new Set<FieldKey>();

  const set = (key: Exclude<FieldKey, "soft" | "priorities">, value: string) => {
    if (profile[key] !== value) {
      profile[key] = value;
      changed.add(key);
    }
  };
  const addSoft = (trait: string) => {
    if (!profile.soft.includes(trait)) {
      profile.soft.push(trait);
      changed.add("soft");
    }
  };

  if (/(\bit\b|айти|\bcs\b|computer|программир|информат|разработ)/.test(text)) set("direction", "Computer Science");
  else if (/бизнес|менеджм|экономик|финанс|маркетинг/.test(text)) set("direction", "Бизнес");
  else if (/медиц|врач|биолог/.test(text)) set("direction", "Медицина");
  else if (/дизайн|искусств|архитект/.test(text)) set("direction", "Дизайн и искусство");
  else if (/инженер|робот|физик/.test(text)) set("direction", "Инженерия");

  const warm = /тепл|жарк|солн/.test(text);
  if (/европ/.test(text) && (warm || /южн|испан|итал|португал/.test(text))) set("location", "Южная, Западно-Южная Европа");
  else if (/европ|герман|франц|нидерланд|швейц/.test(text)) set("location", "Европа");
  else if (/сша|америк|штат/.test(text)) set("location", "США");
  else if (/канад/.test(text)) set("location", "Канада");
  else if (/казахстан|алмат|астан/.test(text)) set("location", "Казахстан");
  else if (/ази|коре|япон|китай|сингапур/.test(text)) set("location", "Азия");

  // The question being answered: a bare number in reply to the budget question is a budget
  const pending = nextMissing(current);

  // A sum of money: with a currency, or a plain number in a message about money
  // (exam scores are cut out first so "SAT 1300" is not read as a budget)
  const withoutScores = text.replace(/(sat|ielts|ент|унт)\D{0,12}\d+(?:[.,]\d)?/g, " ");
  const moneyContext = /бюджет|грант|стоим|плат|в год|денег|деньги|\$|долл|usd|евро|€|тенге/.test(withoutScores) || pending === "budget";
  const money =
    withoutScores.match(/(\d[\d\s]{2,})\s*(?:\$|долл|usd|€|евро)/) ??
    (moneyContext ? withoutScores.match(/(?:^|\D)(\d{3,}(?:\s\d{3})*)(?!\d)/) : null);
  if (money && Number(money[1].replace(/\s/g, "")) >= 300) set("budget", `до ${money[1].replace(/\s/g, "")}$ в год`);
  else if (/только (на )?грант|без гранта не|бесплатн/.test(text)) set("budget", "нужен грант");
  else if (/недорог|дешев|бюджетн|небольш(ой|ие) (бюджет|деньги)|мало денег/.test(text)) set("budget", "небольшой, до 3000$");
  else if (/бюджет не важ|деньги не важ|не ограничен/.test(text)) set("budget", "не ограничен");

  const sat = text.match(/sat\D{0,12}(\d{3,4})/);
  if (sat) set("sat", sat[1]);
  else if (/sat[^.]*ноябр/.test(text)) set("sat", "План на ноябрь");
  else if (/sat[^.]*(не сдавал|нет)|не сдавал[^.]*sat/.test(text)) set("sat", "не сдавал");

  const ielts = text.match(/ielts\D{0,12}(\d(?:[.,]\d)?)/);
  if (ielts) set("ielts", ielts[1].replace(",", "."));
  else if (/ielts[^.]*(не сдавал|нет)|не сдавал[^.]*ielts/.test(text)) set("ielts", "не сдавал, считаем как 6.0");

  const grade = text.match(/(?:^|\D)(9|10|11)\s*(?:-?й\s*)?класс/);
  if (grade) set("grade", `${grade[1]} класс`);

  if (/(на|по)[- ]?английск|english/.test(text)) set("language", "английский");
  else if (/(на|по)[- ]?русск/.test(text)) set("language", "русский");
  else if (/(на|по)[- ]?казахск/.test(text)) set("language", "казахский");

  if (/только (на )?грант|без гранта не/.test(text)) set("grant", "только грант");
  else if (/грант[^.]*не нуж|без гранта/.test(text)) set("grant", "не нужен");
  else if (/грант[^.]*желательн|желательн[^.]*грант/.test(text)) set("grant", "желательно");
  else if (/грант/.test(text)) set("grant", "нужен");

  const ent = text.match(/(ент|унт)\D{0,12}(\d{2,3})/);
  if (ent) set("ent", ent[2]);

  // Short answers to the question that is currently open ("нет", "не знаю")
  const shortNo = /^\s*(нет|неа|не сдавал\w*|пока нет|еще нет|ничего)\s*[.!]?\s*$/.test(text);
  const shortUnknown = /^\s*(не знаю|хз|пока не знаю|не решил\w*|без разницы)\s*[.!]?\s*$/.test(text);
  if (pending === "exams" && (shortNo || shortUnknown)) {
    set("ielts", "не сдавал, считаем как 6.0");
    set("sat", "не сдавал");
  }
  if (pending === "budget" && (shortNo || shortUnknown)) set("budget", "пока не знаю");

  if (/олимпиад/.test(text)) set("strong", /междунар/.test(text) ? "Участник международных олимпиад" : "Участник олимпиад");

  if (warm) addSoft("Любит теплые климаты");
  if (/мегаполис|больш(ой|их|ие) город/.test(text)) addSoft("не любит мегаполисы");
  if (/небольш(ой|их|ие) город|маленьк(ий|их|ие) город/.test(text)) addSoft("предпочитает небольшие города");
  if (/банан/.test(text)) addSoft("Любит бананы");
  if (/наук|исследов|лаборатор/.test(text)) addSoft("хочет заниматься наукой");
  if (/обмен/.test(text)) addSoft("важен обмен");

  // Ограничения (§3.1): «обязательно» / «точно не» — простая эвристика, правится вручную в профиле
  const required = text.match(/обязательно(?:,?\s*чтобы|,?\s*что)?\s+(.+?)[.!]?$/);
  if (required && required[1].length < 80) set("requiredNote", required[1].trim());
  const excluded = text.match(/(?:точно не |искл(?:ючи|ючить)\s+)(.+?)[.!]?$/);
  if (excluded && excluded[1].length < 80) set("excludedNote", excluded[1].trim());

  // Темп и стиль (§3.1)
  const hours = text.match(/(\d{1,2})\s*час\w*\s*(?:в\s*недел|\/\s*нед)/);
  if (hours) set("paceHours", `${hours[1]} ч/нед`);
  if (/объясняй (подробн|детальн)|глубже объясня|подробнее, пожалуйста/.test(text)) set("paceDepth", "глубоко");
  else if (/коротк(о|ие) объясн|кратко объясня/.test(text)) set("paceDepth", "коротко");
  if (/подскаж(и|ите) сразу|давай (больше )?подсказ/.test(text)) set("paceHint", "щедро");
  else if (/без подсказ|сам разберусь|минимум подсказ/.test(text)) set("paceHint", "минимум");

  return { profile, changed: [...changed] };
}

/** A fully filled profile reaches 75%; the last quarter comes from confirming the summary. */
export function readiness(profile: Profile, confirmed: boolean): number {
  if (confirmed) return 100;
  let score = 0;
  if (profile.direction) score += 20;
  if (profile.location) score += 15;
  if (profile.budget || profile.grant) score += 15;
  if (profile.sat || profile.ielts || profile.ent) score += 15;
  if (profile.soft.length || profile.strong) score += 10;
  return score;
}

export function nextMissing(profile: Profile): MissingKey | null {
  if (!profile.direction) return "direction";
  if (!profile.location) return "location";
  if (!profile.sat && !profile.ielts && !profile.ent) return "exams";
  // An answer about the grant also counts as an answer about money
  if (!profile.budget && !profile.grant) return "budget";
  return null;
}

export function placeholderFor(profile: Profile): string {
  const missing = nextMissing(profile);
  return missing ? QUESTIONS[missing].hint : "Расскажи ещё что-нибудь о себе...";
}

export function summaryText(profile: Profile): string {
  const dir = profile.direction === "Computer Science" ? "IT" : profile.direction;
  const warm = profile.soft.includes("Любит теплые климаты");
  const locations: Record<string, string> = {
    "Южная, Западно-Южная Европа": warm ? "теплой Европе" : "Южной Европе",
    Европа: warm ? "теплой Европе" : "Европе",
    США: "США",
    Канада: "Канаде",
    Казахстан: "Казахстане",
    Азия: "Азии",
  };

  const parts = [`${dir} в ${locations[profile.location ?? ""] ?? profile.location}`];
  if (!profile.ielts || profile.ielts.startsWith("не сдавал")) parts.push("IELTS считаем как 6.0");
  else parts.push(`IELTS ${profile.ielts}`);
  if (profile.strong) parts.push(profile.strong.toLowerCase());
  return parts.join(", ");
}

/* ---------- Student profile view ---------- */

/** said — the student told us (or edited it); assumed — our default until they say otherwise. */
export type FieldStatus = "said" | "assumed";
export type ProfileItem = { key: FieldKey; label: string; value: string; status: FieldStatus; chips?: string[] };

const labelOf = (key: FieldKey) => FIELDS.find(([k]) => k === key)![1];

/**
 * What the profile panel shows: only fields we know or assume, nothing that is still missing.
 * Later the backend decides this; for now a few defaults stand in for its assumptions.
 */
export function profileItems(profile: Profile): ProfileItem[] {
  const items: ProfileItem[] = [];
  const add = (key: FieldKey, assumed?: string) => {
    const value = fieldValue(profile, key);
    if (value) items.push({ key, label: labelOf(key), value, status: "said" });
    else if (assumed) items.push({ key, label: labelOf(key), value: assumed, status: "assumed" });
  };

  add("grade", "11 класс");
  add("direction");
  add("location");
  add("language", profile.location === "Казахстан" ? "Русский или казахский" : "Английский");
  if (profile.ielts?.startsWith("не сдавал")) {
    items.push({ key: "ielts", label: "IELTS", value: "6.0 — пока не сдавал", status: "assumed" });
  } else {
    add("ielts", "6.0");
  }
  add("sat");
  add("ent");
  add("budget");
  add("grant", "Желательно");
  add("strong");
  if (profile.soft.length) {
    items.push({
      key: "soft",
      label: labelOf("soft"),
      value: profile.soft.join(", "),
      status: "said",
      chips: profile.soft.map((t) => t.charAt(0).toUpperCase() + t.slice(1)),
    });
  }
  add("requiredNote");
  add("excludedNote");
  items.push({
    key: "priorities",
    label: labelOf("priorities"),
    value: profile.priorities.map((k) => PRIORITY_LABEL[k]).join(" › "),
    status: profile.priorities.every((k, i) => k === PRIORITY_KEYS[i]) ? "assumed" : "said",
  });
  add("paceHours", "2-3 ч/нед");
  add("paceDepth", "обычная");
  add("paceHint", "обычный");
  return items;
}

/** Apply a manual edit from the profile panel; an empty value clears the field. */
export function editField(profile: Profile, key: FieldKey, raw: string): Profile {
  const value = raw.trim();
  const next: Profile = { ...profile, soft: [...profile.soft], priorities: [...profile.priorities] };
  if (key === "soft") {
    next.soft = value.split(",").map((t) => t.trim()).filter(Boolean);
  } else if (key === "priorities") {
    const keys = value
      .split(",")
      .map((s) => s.trim())
      .filter((s): s is PriorityKey => (PRIORITY_KEYS as string[]).includes(s));
    if (keys.length === PRIORITY_KEYS.length) next.priorities = keys;
  } else {
    next[key] = value || undefined;
  }
  return next;
}

function acknowledge(profile: Profile, changed: FieldKey[]): string {
  if (changed.includes("location") && profile.location?.startsWith("Южная")) return "Хорошо, смотрим на Южную Европу.";
  if (!changed.length) return "Понял.";
  // Keep acronyms (IELTS, SAT, ЕНТ) as they are
  const labels = changed.map((key) => {
    const label = labelOf(key);
    return label === label.toUpperCase() ? label : label.toLowerCase();
  });
  return `Записал: ${labels.join(", ")}.`;
}

export type Reply = { text: string; summary: boolean };

/** Decide what the assistant says after a message has been applied to the profile. */
export function planReply(
  profile: Profile,
  changed: FieldKey[],
  { summarySent, fromEdit }: { summarySent: boolean; fromEdit: boolean }
): Reply {
  if (fromEdit) {
    return { text: `Учёл правку. Обновил резюме понимания: ${summaryText(profile)}`, summary: true };
  }

  const missing = nextMissing(profile);
  if (missing && !(summarySent && missing === "budget")) {
    return { text: `${acknowledge(profile, changed)} ${QUESTIONS[missing].ask}`, summary: false };
  }

  if (!summarySent) {
    return { text: `Принял. Собрал резюме понимания: ${summaryText(profile)}`, summary: true };
  }

  return {
    text: changed.length
      ? `${acknowledge(profile, changed)} Профиль обновлён.`
      : "Понял тебя. Если что-то поменялось — просто напиши.",
    summary: false,
  };
}

export const CONFIRM_REPLY =
  "Отлично, резюме подтверждено! Вот программы под твой профиль — сохраняй понравившиеся ☆ и сравнивай. Все они есть в панели «Программы» слева.";
