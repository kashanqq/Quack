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
  dateKey,
  examMilestoneId,
  plannedTest,
  type DatedExam,
  type ExamId,
  type ExamOutlook,
} from "./prepData";
import { chooseTestDate, proposedSet, readiness, type PrepModel, type PrepSub, type PrepTab } from "./prepModel";
import { StateGlyph } from "./SkillGraph";
import { SetDetail } from "./SetDetail";
import { DiagnosticMock } from "./DiagnosticMock";
import type { DiagnosticResultSummary } from "./diagnosticData";
import { PixelDuck } from "../duck/PixelDuck";
import styles from "./prep.module.css";

type Props = {
  model: PrepModel;
  programs: Program[];
  sub: PrepSub;
  /** Jump to another tab, optionally straight to one of its sub-tabs */
  onGo: (tab: PrepTab, sub?: PrepSub, exam?: ExamId) => void;
  /** Opens a set: the active one in «Сейчас», any other in «Маршрут» */
  onOpenSet: (setId: string, topic?: string) => void;
  onAccept: (setId: string) => void;
  onModel: (model: PrepModel) => void;
  onToast: (text: string) => void;
  /** A topic of the active set asked for from elsewhere; `n` changes on every ask so it opens again */
  focus: { topic?: string; n: number } | null;
  diagnostic: {
    /** The test is on screen (first visit after the start button, or a retake) */
    open: boolean;
    onStart: () => void;
    onClose?: () => void;
    onComplete: (summary: DiagnosticResultSummary) => void;
    onSkip: () => void;
  };
};

/**
 * §4.1 — the section's overview in two sub-tabs. «Сейчас» is the one way in: the entrance test on
 * the first visit, then the active set itself — its graph of topics, the chat and the mocks.
 */
export function Overview({ model, programs, sub, onGo, onOpenSet, onAccept, onModel, onToast, focus, diagnostic }: Props) {
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
  const exams = requirements(programs, outlook, model.testDates);
  const list = milestones(programs, model.testDates);

  if (sub === "requirements")
    return (
      <Requirements
        exams={exams}
        milestoneList={list}
        done={model.milestonesDone}
        onPick={(exam, key) => {
          onModel(chooseTestDate(model, exam, key));
          onToast(`Тест ${EXAMS[exam].name} — ${formatDate(new Date(`${key}T00:00`))}. Вехи и прогноз пересчитаны`);
        }}
      >
        <Important model={model} milestoneList={list} onGo={onGo} onOpenSet={onOpenSet} />
      </Requirements>
    );
  return (
    <Now
      model={model}
      forecasts={{ sat: series.sat.forecast, ent: series.ent.forecast }}
      onGo={onGo}
      onAccept={onAccept}
      onModel={onModel}
      onToast={onToast}
      focus={focus}
      diagnostic={diagnostic}
    />
  );
}

/* ---------- Сейчас: the entrance test, then the active set right here ---------- */

const DUCK_TEMPO = ["fast", "fast", "steady", "chill"] as const;

type Pace = { id: string; name: string; level: 0 | 1 | 2 | 3; verdict: string; summary: string };

function Now({
  model,
  forecasts,
  onGo,
  onAccept,
  onModel,
  onToast,
  focus,
  diagnostic,
}: {
  model: PrepModel;
  forecasts: Record<ExamId, Date>;
  onGo: (tab: PrepTab, sub?: PrepSub, exam?: ExamId) => void;
  onAccept: (setId: string) => void;
  onModel: (model: PrepModel) => void;
  onToast: (text: string) => void;
  focus: Props["focus"];
  diagnostic: Props["diagnostic"];
}) {
  const { state } = useQuack();
  const current = model.currentSet ? setById(model.currentSet) : null;
  const isDiagPending = !model.diagnosticDone;

  // Quack's verdict per exam; demo programs are not saved, so there only the forecast date
  const paces: Pace[] = state.standing?.exams.length
    ? state.standing.exams.map((e) => ({ id: e.id, name: e.name, level: e.level, verdict: e.verdict, summary: e.summary }))
    : EXAM_IDS.map((id) => {
        const test = plannedTest(id, model.testDates) ?? EXAMS[id].test;
        return {
          id,
          name: EXAMS[id].name,
          level: forecasts[id] <= test ? 3 : 0,
          verdict: forecasts[id] <= test ? "Успеваешь" : "Не успеваешь",
          summary: `прогноз на ${formatDate(forecasts[id])}, тест ${formatDate(test)}`,
        };
      });

  // The test itself, in place: its result builds the route and the first set opens on the same spot
  if (diagnostic.open)
    return (
      <DiagnosticMock
        onComplete={diagnostic.onComplete}
        onClose={diagnostic.onClose}
        onSkip={isDiagPending ? diagnostic.onSkip : undefined}
      />
    );

  // The active set is the screen: its topics on their timeline, a topic opens the chat and the mock
  if (!isDiagPending && current)
    return (
      <div className={styles.nowWork}>
        <div className={styles.nowStrip}>
          <ul className={styles.nowStripPaces} aria-label="Темп по экзаменам">
            {paces.map((p) => (
              <li key={p.id} data-pace={p.level} title={p.summary}>
                <PixelDuck tempo={DUCK_TEMPO[p.level]} className={styles.nowStripDuck} asleep={p.level === 0} />
                <span className={styles.nowPaceName}>{p.name}</span>
                <strong>{p.verdict}</strong>
              </li>
            ))}
          </ul>
          <button type="button" className={styles.link} onClick={() => onGo("sets", "route")}>
            Сменить сет →
          </button>
        </div>
        <SetDetail
          key={`${current.id}-${focus?.n ?? 0}`}
          model={model}
          set={current}
          topic={focus?.topic}
          onMakeCurrent={onAccept}
          onModel={onModel}
          onToast={onToast}
        />
      </div>
    );

  const proposed = isDiagPending ? null : proposedSet(model);
  const topicId = proposed?.skills.find((id) => model.states[id] !== "solid") ?? proposed?.skills[0];
  const topic = topicId ? skillById(topicId) : null;

  return (
    <div className={styles.nowScreen}>
      <section className={styles.nowCenter} aria-label="Сейчас">
        <PixelDuck tempo="steady" className={styles.nowDuck} waving />
        {isDiagPending ? (
          <>
            <h2 className={styles.nowSet}>Входной замер готовности</h2>
            <p className={styles.nowTopic}>
              <Icon name="sparkles" size={14} />8 вопросов · по ответам соберётся твой первый сет
            </p>
          </>
        ) : proposed && topic ? (
          <>
            <p className={styles.eyebrow}>Ассистент предлагает начать с</p>
            <h2 className={styles.nowSet}>
              Сет {proposed.number} · {proposed.title}
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

        {isDiagPending ? (
          <div className={styles.nowDiagActionBlock}>
            <button
              type="button"
              className={styles.nowButton}
              aria-label="Начать замер"
              title="Начать замер"
              onClick={diagnostic.onStart}
            >
              <Icon name="play" size={26} />
            </button>
            <span className={styles.nowActionHint}>Нажми, чтобы начать — это пара минут</span>
            <button
              type="button"
              className={styles.nowSkipBtn}
              onClick={diagnostic.onSkip}
              title="Использовать начальные базовые оценки без прохождения теста"
            >
              Пропустить тест (взять базовые оценки)
            </button>
          </div>
        ) : (
          proposed && (
            <button type="button" className={styles.nowButton} aria-label="Начать" title="Начать" onClick={() => onAccept(proposed.id)}>
              <Icon name="play" size={26} />
            </button>
          )
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
function Requirements({
  exams,
  milestoneList,
  done,
  onPick,
  children,
}: {
  exams: ReturnType<typeof requirements>;
  milestoneList: ReturnType<typeof milestones>;
  done: string[];
  /** The student picks the sitting: its `dateKey` */
  onPick: (exam: DatedExam, key: string) => void;
  children: React.ReactNode;
}) {
  return (
    <div className={styles.canvasGrid}>
      {exams.map((exam) => {
        const margin = exam.testDate && exam.forecast ? daysBetween(exam.forecast, exam.testDate) : 0;
        const dated = exam.id === "ielts" ? null : exam.id;
        const registration = dated && exam.testDate ? milestoneList.find((m) => m.id === examMilestoneId(dated, "reg", exam.testDate!)) : undefined;
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
                {dated && exam.testCandidates.length > 1 ? (
                  // The student decides the date; each sitting says what it leaves by the forecast
                  <dd className={styles.testDates} role="radiogroup" aria-label={`Дата теста ${exam.name}`}>
                    {exam.testCandidates.map((d) => {
                      const chosen = exam.testDate?.getTime() === d.getTime();
                      const room = exam.forecast ? daysBetween(exam.forecast, d) : null;
                      return (
                        <button
                          key={d.getTime()}
                          type="button"
                          role="radio"
                          aria-checked={chosen}
                          className={styles.testDate}
                          data-late={room !== null && room < 0 ? "" : undefined}
                          onClick={() => !chosen && onPick(dated, dateKey(d))}
                        >
                          <b>{formatShort(d)}</b>
                          {room !== null && <span>{room >= 0 ? `запас ${room} дн.` : `не хватает ${-room} дн.`}</span>}
                        </button>
                      );
                    })}
                  </dd>
                ) : (
                  <dd>{exam.testDate ? formatDate(exam.testDate) : "—"}</dd>
                )}
              </div>
              {registration && (
                <div>
                  <dt>Регистрация</dt>
                  <dd>
                    до {formatDate(registration.date)}
                    {done.includes(registration.id) ? (
                      <span className={styles.ok}> · ✓ отмечена</span>
                    ) : (
                      <span className={styles.muted} title="Отметить можно в календаре Quack или написать в чате: «зарегистрировался на SAT»">
                        {" "}
                        · ещё не отмечена
                      </span>
                    )}
                  </dd>
                </div>
              )}
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
