// A milestone told in the choice chat: «зарегистрировался на SAT», «подал в Болонью». The chat ticks it the
// same way the calendar and the Quack feed do (product-logic §3.2: an action in the chat is a tool call).
// Keyword rules stand in for the backend's assistant. Pure functions, no React.

import { milestones } from "../prep/prepData";
import { programById, PROGRAMS } from "./programs";

export type MilestoneIntent =
  /** Done, and one of the student's milestones */
  | { kind: "done"; id: string; title: string }
  /** Only planned: nothing is ticked, the assistant asks */
  | { kind: "planned"; what: string }
  /** Done, but no saved program has such a date */
  | { kind: "unknown"; what: string };

/** Ways the programs are named in a message, beyond the city */
const ALIASES: Record<string, string[]> = {
  valencia: ["valenc", "валенс"],
  sapienza: ["sapienz", "сапиенц", "рим"],
  bologna: ["bologn", "болон"],
  porto: ["porto", "порту"],
  lisbon: ["lisbo", "tecnico", "лиссаб"],
  eth: ["eth", "цюрих", "zurich", "zürich"],
};

const word = (stem: string) => new RegExp(`(^|[^a-zа-я])${stem}`);

const DONE_REG = /зарегистрировал(ся|ась)|записал(ся|ась) на/;
const DONE_TEST = /(^|[^а-я])сдал(а)?([^а-я]|$)/;
const DONE_APPLY = /(^|[^а-я])(подал(а)?|отправил(а)?)([^а-я]|$)/;
const PLANNED = /собира|планиру|зарегистрир(уюсь|оваться)|запишусь|записаться|подам|подать|сдам|сдать/;
/** «SAT не сдавал» is what the profile hears, not a date: denials are left to it */
const DENIED = /(^|[^а-я])(не|еще не|пока не) (зарегистр|записал|пода|отправ|сда)/;

function examIn(text: string): "sat" | "ent" | null {
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

/** What the message says about a milestone, or null when it is not about one. */
export function milestoneIntent(raw: string, saved: string[]): MilestoneIntent | null {
  const text = raw.toLowerCase().replace(/ё/g, "е");
  const exam = examIn(text);
  const program = programIn(text);

  // «Сдал SAT на 1400» is a score for the profile, not a date
  const reg = exam && /регистр|запис/.test(text) ? `${exam}-reg` : null;
  const test = exam && !reg && /(^|[^а-я])сда(л|м|ть)/.test(text) && !/\d{2,}/.test(text) ? `${exam}-test` : null;
  const apply = program && /(^|[^а-я])(пода|отправ)|заявк|документ/.test(text) ? `apply-${program}` : null;
  const id = reg ?? test ?? apply;
  // Before anything is saved, talk about exams and applications is the student telling us about themselves
  if (!id || !saved.length || DENIED.test(text)) return null;

  const names: Record<string, string> = {
    "sat-reg": "регистрацию на SAT",
    "sat-test": "тест SAT",
    "ent-reg": "регистрацию на ЕНТ",
    "ent-test": "ЕНТ",
  };
  const what = names[id] ?? `подачу в ${programById(program!).university}`;

  if (PLANNED.test(text)) return { kind: "planned", what };
  // Only a past-tense verb ticks: «регистрация на SAT» on its own says nothing about whether it is done
  if (!(DONE_REG.test(text) || DONE_TEST.test(text) || DONE_APPLY.test(text))) return null;

  const mine = milestones(saved.map(programById).filter(Boolean)).find((m) => m.id === id);
  return mine ? { kind: "done", id, title: mine.title } : { kind: "unknown", what };
}
