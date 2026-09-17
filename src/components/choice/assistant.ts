// Simulated assistant for the "Choice" page (front-end only): keyword rules that fill the
// profile, pick the next question and phrase the summary. Pure functions, no React.

export type Profile = {
  direction?: string;
  location?: string;
  budget?: string;
  sat?: string;
  ielts?: string;
  strong?: string;
  soft: string[];
};

export type FieldKey = Exclude<keyof Profile, "soft"> | "soft";

export const FIELDS: [FieldKey, string][] = [
  ["direction", "Направление"],
  ["location", "Локация"],
  ["budget", "Бюджет"],
  ["sat", "SAT"],
  ["ielts", "IELTS"],
  ["strong", "Сильные черты"],
  ["soft", "Мягкие черты"],
];

export const EMPTY_PROFILE: Profile = { soft: [] };

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
  const value = key === "soft" ? profile.soft.join(", ") : profile[key];
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : undefined;
}

/** Pull whatever we can recognise out of a message. */
export function extract(current: Profile, raw: string): { profile: Profile; changed: FieldKey[] } {
  const text = raw.toLowerCase().replace(/ё/g, "е");
  const profile: Profile = { ...current, soft: [...current.soft] };
  const changed = new Set<FieldKey>();

  const set = (key: Exclude<FieldKey, "soft">, value: string) => {
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

  const money = text.match(/(\d[\d\s]{2,})\s*(\$|долл|usd)/);
  if (money) set("budget", `до ${money[1].replace(/\s/g, "")}$ в год`);
  else if (/грант|бесплатн/.test(text)) set("budget", "нужен грант");
  else if (/недорог|дешев|бюджетн|небольш(ой|ие) (бюджет|деньги)|мало денег/.test(text)) set("budget", "небольшой, до 3000$");
  else if (/бюджет не важ|деньги не важ|не ограничен/.test(text)) set("budget", "не ограничен");

  const sat = text.match(/sat\D{0,12}(\d{3,4})/);
  if (sat) set("sat", sat[1]);
  else if (/sat[^.]*ноябр/.test(text)) set("sat", "План на ноябрь");
  else if (/sat[^.]*(не сдавал|нет)|не сдавал[^.]*sat/.test(text)) set("sat", "не сдавал");

  const ielts = text.match(/ielts\D{0,12}(\d(?:[.,]\d)?)/);
  if (ielts) set("ielts", ielts[1].replace(",", "."));
  else if (/ielts[^.]*(не сдавал|нет)|не сдавал[^.]*ielts/.test(text)) set("ielts", "не сдавал, считаем как 6.0");

  if (/олимпиад/.test(text)) set("strong", /междунар/.test(text) ? "Участник международных олимпиад" : "Участник олимпиад");

  if (warm) addSoft("Любит теплые климаты");
  if (/мегаполис|больш(ой|их|ие) город/.test(text)) addSoft("не любит мегаполисы");
  if (/небольш(ой|их|ие) город|маленьк(ий|их|ие) город/.test(text)) addSoft("предпочитает небольшие города");
  if (/банан/.test(text)) addSoft("Любит бананы");
  if (/наук|исследов|лаборатор/.test(text)) addSoft("хочет заниматься наукой");
  if (/обмен/.test(text)) addSoft("важен обмен");

  return { profile, changed: [...changed] };
}

/** A fully filled profile reaches 75%; the last quarter comes from confirming the summary. */
export function readiness(profile: Profile, confirmed: boolean): number {
  if (confirmed) return 100;
  let score = 0;
  if (profile.direction) score += 20;
  if (profile.location) score += 15;
  if (profile.budget) score += 15;
  if (profile.sat || profile.ielts) score += 15;
  if (profile.soft.length || profile.strong) score += 10;
  return score;
}

export function nextMissing(profile: Profile): MissingKey | null {
  if (!profile.direction) return "direction";
  if (!profile.location) return "location";
  if (!profile.sat && !profile.ielts) return "exams";
  if (!profile.budget) return "budget";
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

function acknowledge(profile: Profile, changed: FieldKey[]): string {
  if (changed.includes("location") && profile.location?.startsWith("Южная")) return "Хорошо, смотрим на Южную Европу.";
  if (!changed.length) return "Понял.";
  const labels = changed.map((key) => FIELDS.find(([k]) => k === key)![1].toLowerCase());
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
  "Отлично, резюме подтверждено! Дальше подберу программы под тебя — они появятся в разделе «Программы».";
