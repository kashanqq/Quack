// The Quack planner (arch-logic L4 «Планировщик Quack»): compares the standing the student saw on their
// last visit with the one now and turns every difference into a signal. Stateless on purpose — the
// same two standings always give the same signals, so a change that is undone before the student
// looks never makes the button glow. Pure functions, no React, no storage.

import { daysBetween } from "../prep/prepData";
import type { ProgramChance, Signal, Standing } from "./contract";
import { LEVEL_RANK } from "./standing";

export type Draft = Omit<Signal, "at" | "cause">;

/** A first visit has nothing to compare with: only standing alerts (dates, conflicts) count as new. */
export const firstBaseline = (standing: Standing): Standing => ({ ...standing, alerts: [] });

/** A change of the index smaller than this is noise, not news. */
const INDEX_STEP = 4;
const FORECAST_STEP = 2;

/** The fact that moved the most between two readings of a program, in words. */
function factChange(was: ProgramChance, now: ProgramChance): string | undefined {
  let best: { text: string; size: number } | undefined;
  for (const f of now.facts) {
    const old = was.facts.find((x) => x.key === f.key);
    if (old && old.have === f.have && old.need === f.need) continue;
    const size = old && old.margin !== null && f.margin !== null ? Math.abs(f.margin - old.margin) : Infinity;
    const text = old ? `${f.label}: ${old.have} → ${f.have}, нужно ${f.need}` : `${f.label}: ${f.have}, нужно ${f.need}`;
    if (!best || size > best.size) best = { text, size };
  }
  return best?.text;
}

/** How the exam targets moved when the saved list changed. */
function targetsChange(was: Standing, now: Standing): string {
  const parts: string[] = [];
  for (const e of was.exams) {
    const after = now.exams.find((x) => x.id === e.id);
    if (!after) parts.push(`${e.name} больше не нужен`);
    else if (after.target !== e.target) parts.push(`цель ${e.name}: ${e.target} → ${after.target}`);
  }
  for (const e of now.exams) if (!was.exams.some((x) => x.id === e.id)) parts.push(`добавился ${e.name}, цель ${e.target}`);
  return parts.length ? parts.join("; ") : "требования к экзаменам не изменились";
}

const needs = (p: ProgramChance) =>
  p.facts
    .filter((f) => f.key !== "budget")
    .map((f) => `${f.label.replace(" по прогнозу", "")} от ${f.need}`)
    .join(", ");

export function plan(seen: Standing, now: Standing): Draft[] {
  const out: Draft[] = [];

  // Dates coming up, slept through, in conflict; a set past its deadline
  const seenAlerts = new Set(seen.alerts.map((a) => a.id));
  for (const a of now.alerts) {
    if (seenAlerts.has(a.id)) continue;
    out.push({
      id: a.id,
      level: a.level,
      tone: a.kind === "deadline" ? "info" : "down",
      kind: a.kind,
      title: a.title,
      detail: a.detail,
      target: a.kind === "late-set" || a.kind === "missed" ? "prep" : "calendar",
    });
  }

  // Pace: a new verdict, or the same verdict with a forecast that moved
  if (now.pace) {
    const was = seen.pace;
    if (!was || was.level !== now.pace.level) {
      const worse = !was || now.pace.level < was.level;
      if (was || now.pace.level <= 1) {
        out.push({
          id: `pace-${now.pace.level}`,
          level: worse && now.pace.level === 0 ? "urgent" : "notice",
          tone: worse ? "down" : "up",
          kind: "pace",
          title: was ? `Темп: ${was.verdict.toLowerCase()} → ${now.pace.verdict.toLowerCase()}` : `Темп: ${now.pace.verdict.toLowerCase()}`,
          detail: now.pace.summary,
          subject: now.pace.exam,
          target: "prep",
        });
      }
    } else {
      const before = seen.exams.find((e) => e.id === now.pace!.exam)?.forecast;
      const after = now.exams.find((e) => e.id === now.pace!.exam)?.forecast;
      const shift = before && after ? daysBetween(new Date(before), new Date(after)) : 0;
      if (Math.abs(shift) >= FORECAST_STEP) {
        out.push({
          id: `forecast-${shift > 0 ? "later" : "earlier"}`,
          level: "notice",
          tone: shift > 0 ? "down" : "up",
          kind: "pace",
          title: shift > 0 ? `Шансы успеть к тесту ниже: прогноз на ${shift} дн. позже` : `Шансы успеть к тесту выше: прогноз на ${-shift} дн. раньше`,
          detail: now.pace.summary,
          subject: now.pace.exam,
          target: "prep",
        });
      }
    }
  }

  // Saved programs that came or went
  const before = new Map(seen.programs.map((p) => [p.id, p]));
  const after = new Set(now.programs.map((p) => p.id));
  for (const p of now.programs) {
    if (before.has(p.id)) continue;
    out.push({
      id: `added-${p.id}`,
      level: "notice",
      tone: "info",
      kind: "programs",
      title: `Добавлена ${p.university}`,
      detail: `${p.levelLabel} · ${needs(p)}`,
      subject: p.id,
      target: "programs",
    });
  }
  for (const p of seen.programs) {
    if (after.has(p.id)) continue;
    out.push({
      id: `removed-${p.id}`,
      level: "notice",
      tone: "info",
      kind: "programs",
      title: `Убрана ${p.university}`,
      detail: targetsChange(seen, now),
      subject: p.id,
      target: "programs",
    });
  }

  // Chances of the programs that stayed: a new level, or the same level with facts that moved
  for (const p of now.programs) {
    const was = before.get(p.id);
    if (!was) continue;
    const because = factChange(was, p);
    if (p.level !== was.level) {
      const worse = LEVEL_RANK[p.level] < LEVEL_RANK[was.level];
      out.push({
        id: `chance-${p.id}-${p.level}`,
        level: worse ? "urgent" : "notice",
        tone: worse ? "down" : "up",
        kind: "chance",
        title: `Шансы на ${p.university} ${worse ? "снизились" : "выросли"}`,
        detail: [`${was.levelLabel} → ${p.levelLabel}`, because].filter(Boolean).join(" · "),
        subject: p.id,
        target: "programs",
      });
    } else if (Math.abs(p.index - was.index) >= INDEX_STEP) {
      const up = p.index > was.index;
      out.push({
        id: `chance-${p.id}-${up ? "up" : "down"}`,
        level: "notice",
        tone: up ? "up" : "down",
        kind: "chance",
        title: `Шансы на ${p.university} ${up ? "выше" : "ниже"}`,
        detail: [because, `по-прежнему ${p.levelLabel}`].filter(Boolean).join(" · "),
        subject: p.id,
        target: "programs",
      });
    }
  }

  // Urgent first; otherwise the order above: dates, pace, programs, chances
  return out.map((d, i) => ({ d, i })).sort((a, b) => Number(b.d.level === "urgent") - Number(a.d.level === "urgent") || a.i - b.i).map(({ d }) => d);
}
