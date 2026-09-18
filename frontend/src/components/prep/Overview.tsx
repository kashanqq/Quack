"use client";

import { Icon } from "../choice/Icon";
import type { Program } from "../choice/programs";
import { useQuack } from "../quack/source";
import { routeDelay } from "../quack/standing";
import {
  daysBetween,
  formatDate,
  formatShort,
  forecastSeries,
  milestones,
  requirements,
  SETS,
  setById,
  skillById,
  SKILLS,
  TODAY,
  EXAM_IDS,
  EXAMS,
  type ExamId,
  type ExamOutlook,
} from "./prepData";
import { proposedSet, readiness, type PrepModel, type PrepSub, type PrepTab } from "./prepModel";
import { StateGlyph } from "./SkillGraph";
import { PixelDuck } from "../duck/PixelDuck";
import styles from "./prep.module.css";

type Props = {
  model: PrepModel;
  programs: Program[];
  sub: PrepSub;
  /** Jump to another tab, optionally straight to one of its sub-tabs */
  onGo: (tab: PrepTab, sub?: PrepSub, exam?: ExamId) => void;
  /** Opens a set's graph, optionally with one of its topics selected */
  onOpenSet: (setId: string, topic?: string) => void;
  onAccept: (setId: string) => void;
};

/**
 * §4.1 — the section's overview, split into four sub-tabs so one screen answers one question:
 * what to do now, what the programs demand, which dates are coming, how the programs are changing.
 */
export function Overview({ model, programs, sub, onGo, onOpenSet, onAccept }: Props) {
  // Each exam with a knowledge model has its own readiness, history and forecast
  const series = Object.fromEntries(
    EXAM_IDS.map((id) => {
      const now = readiness(model, id);
      return [id, { readiness: now, ...forecastSeries(now, model.extraDays, id) }];
    })
  ) as Record<ExamId, { readiness: number } & ReturnType<typeof forecastSeries>>;
  const outlook: ExamOutlook = {
    sat: { readiness: series.sat.readiness, forecast: series.sat.forecast },
    ent: { readiness: series.ent.readiness, forecast: series.ent.forecast },
  };
  const exams = requirements(programs, outlook);
  const list = milestones(programs);

  if (sub === "requirements")
    return (
      <Requirements exams={exams}>
        <Important model={model} milestoneList={list} onGo={onGo} onOpenSet={onOpenSet} />
      </Requirements>
    );
  return <Now model={model} forecasts={{ sat: series.sat.forecast, ent: series.ent.forecast }} onOpenSet={onOpenSet} onAccept={onAccept} />;
}

/* ---------- Сейчас: one calm screen — the set and topic in work, the pace per exam, one button ---------- */

const DUCK_TEMPO = ["fast", "fast", "steady", "chill"] as const;

function Now({
  model,
  forecasts,
  onOpenSet,
  onAccept,
}: {
  model: PrepModel;
  forecasts: Record<ExamId, Date>;
  onOpenSet: (setId: string, topic?: string) => void;
  onAccept: (setId: string) => void;
}) {
  const { state } = useQuack();
  const current = model.currentSet ? setById(model.currentSet) : null;
  const set = current ?? proposedSet(model) ?? null;
  // The topic in work: the first one of the set that does not hold yet
  const topicId = set?.skills.find((id) => model.states[id] !== "solid") ?? set?.skills[0];
  const topic = topicId ? skillById(topicId) : null;

  // Quack's verdict per exam; demo programs are not saved, so there only the forecast date
  const paces = state.standing?.exams.length
    ? state.standing.exams.map((e) => ({ id: e.id, name: e.name, level: e.level, verdict: e.verdict, summary: e.summary }))
    : EXAM_IDS.map((id) => ({
        id,
        name: EXAMS[id].name,
        level: (forecasts[id] <= EXAMS[id].test ? 3 : 0) as 0 | 3,
        verdict: forecasts[id] <= EXAMS[id].test ? "Успеваешь" : "Не успеваешь",
        summary: `прогноз на ${formatDate(forecasts[id])}, тест ${formatDate(EXAMS[id].test)}`,
      }));

  return (
    <div className={styles.nowScreen}>
      <section className={styles.nowCenter} aria-label="Сейчас">
        <PixelDuck tempo="steady" className={styles.nowDuck} waving={!set} />
        {set && topic ? (
          <>
            <h2 className={styles.nowSet}>
              Сет {set.number} · {set.title}
            </h2>
            <p className={styles.nowTopic}>
              <StateGlyph state={model.states[topic.id]} size={14} />
              {topic.name}
            </p>
          </>
        ) : (
          <h2 className={styles.nowSet}>Все сеты пройдены — осталось закрепление и тест</h2>
        )}

        <ul className={styles.nowPaces}>
          {paces.map((p) => (
            <li key={p.id} data-pace={p.level}>
              <PixelDuck tempo={DUCK_TEMPO[p.level]} className={styles.nowPaceDuck} asleep={p.level === 0} />
              <span className={styles.nowPaceName}>{p.name}</span>
              <strong>{p.verdict}</strong>
            </li>
          ))}
        </ul>

        {set && topic && (
          <button
            type="button"
            className={styles.nowButton}
            aria-label={current ? "Продолжить" : "Начать"}
            title={current ? "Продолжить" : "Начать"}
            onClick={() => (current ? onOpenSet(set.id) : onAccept(set.id))}
          >
            <Icon name="play" size={26} />
          </button>
        )}
      </section>
    </div>
  );
}

/** The few things worth knowing before anything else: the root of the errors, confirmed traps, what is late, the next date. */
function Important({
  model,
  milestoneList,
  onGo,
  onOpenSet,
}: {
  model: PrepModel;
  milestoneList: ReturnType<typeof milestones>;
  onGo: (tab: PrepTab, sub?: PrepSub, exam?: ExamId) => void;
  onOpenSet: (setId: string, topic?: string) => void;
}) {
  // The set a topic is practised in: an open one first, the current one above all
  const setWith = (skillId: string) =>
    SETS.find((s) => s.id === model.currentSet && s.skills.includes(skillId)) ??
    SETS.find((s) => s.skills.includes(skillId) && !model.doneSets.includes(s.id)) ??
    SETS.find((s) => s.skills.includes(skillId));
  const items: { key: string; tone: "root" | "trap" | "late" | "date"; title: string; text: string; go: () => void; action: string }[] = [];

  for (const root of SKILLS.filter((s) => s.root && model.states[s.id] !== "solid")) {
    const above = SKILLS.filter((s) => s.requires.includes(root.id)).map((s) => s.name.toLowerCase());
    items.push({
      key: `root-${root.id}`,
      tone: "root",
      title: `Корень: ${root.name}`,
      text: above.length ? `из-за него ошибки в теме «${above.join("», «")}»` : "из-за него ошибки выше по карте",
      go: () => onGo("sets", "map", root.exam),
      action: "На карте",
    });
  }

  for (const skill of SKILLS) {
    const trap = model.misconceptions[skill.id].find((m) => m.status === "confirmed");
    if (!trap) continue;
    items.push({
      key: `trap-${skill.id}`,
      tone: "trap",
      title: `Ловушка: ${skill.name}`,
      text: trap.text,
      go: () => {
        const set = setWith(skill.id);
        if (set) onOpenSet(set.id, skill.id);
      },
      action: "Проверить",
    });
  }

  const delay = routeDelay(model);
  if (delay) {
    items.push({
      key: "late",
      tone: "late",
      title: `Сет ${delay.set.number} ещё открыт`,
      text: `срок был ${formatDate(delay.set.deadline)} — прогноз сдвинулся на ${delay.days} дн.`,
      go: () => onOpenSet(delay.set.id),
      action: "Продолжить",
    });
  }

  const next = milestoneList.find((m) => m.date >= TODAY && !model.milestonesDone.includes(m.id));
  if (next) {
    const left = daysBetween(TODAY, next.date);
    items.push({
      key: `date-${next.id}`,
      tone: "date",
      title: next.title,
      text: left === 0 ? "сегодня" : `через ${left} дн. · ${formatDate(next.date)}`,
      go: () => onGo("overview", "requirements"),
      action: "Требования",
    });
  }

  return (
    <section className={`${styles.canvas} ${styles.full}`} aria-label="Важно сейчас">
      <header className={styles.canvasHead}>
        <h3>Важно сейчас</h3>
      </header>
      {items.length === 0 ? (
        <p className={styles.muted}>Корней ошибок и подтверждённых ловушек нет, сроки в порядке.</p>
      ) : (
        <ul className={styles.important}>
          {items.map((item) => (
            <li key={item.key} data-tone={item.tone}>
              <div>
                <strong>{item.title}</strong>
                <span className={styles.muted}>{item.text}</span>
              </div>
              <button type="button" className={styles.link} onClick={item.go}>
                {item.action} →
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/* ---------- Требования: the exams the saved programs ask for ---------- */

/** What each exam asks for and whether the student makes it, in words: no readiness charts or percentages */
function Requirements({ exams, children }: { exams: ReturnType<typeof requirements>; children: React.ReactNode }) {
  return (
    <div className={styles.canvasGrid}>
      {exams.map((exam) => {
        const margin = exam.testDate && exam.forecast ? daysBetween(exam.forecast, exam.testDate) : 0;
        return (
          <section key={exam.id} className={styles.canvas} aria-label={exam.name}>
            <header className={styles.canvasHead}>
              <h3>{exam.name}</h3>
              <span className={styles.demoTag}>демо</span>
            </header>
            <div className={styles.examTarget}>
              <span className={styles.examTargetValue}>{exam.target}</span>
              <span className={styles.examTargetNote}>цель · {exam.targetNote}</span>
            </div>
            <dl className={styles.facts}>
              <div>
                <dt>Тест</dt>
                <dd>
                  {exam.testDate ? formatDate(exam.testDate) : "—"}
                  <span className={styles.muted}> · ещё {exam.testCandidates.slice(1).map(formatShort).join(", ")}</span>
                </dd>
              </div>
              <div>
                <dt>Нужен для</dt>
                {exam.programs.length ? (
                  <dd className={styles.chips}>
                    {exam.programs.map((p) => (
                      <span key={p.id}>{p.university}</span>
                    ))}
                  </dd>
                ) : (
                  <dd>гранта в Казахстане — по нему твой план</dd>
                )}
              </div>
            </dl>
            {exam.hasModel ? (
              <div className={styles.readiness}>
                <p className={margin >= 0 ? styles.ok : styles.warn}>
                  Прогноз {formatDate(exam.forecast!)} —{" "}
                  {margin >= 0 ? `успеваешь, запас ${margin} дн.` : `на ${-margin} дн. позже теста, стоит добавить часов`}
                </p>
              </div>
            ) : (
              <p className={styles.muted}>Без модели знаний: подготовка идёт окнами до дат экзамена, прогноза нет.</p>
            )}
          </section>
        );
      })}

      {/* «Важно сейчас» below the exam targets: «Сейчас» stays a single calm screen */}
      {children}
    </div>
  );
}
