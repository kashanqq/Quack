"use client";

import { Icon } from "../choice/Icon";
import type { Program } from "../choice/programs";
import { useQuack } from "../quack/source";
import { routeDelay } from "../quack/standing";
import { ForecastChart } from "./ForecastChart";
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
  STATE_LABEL,
  TODAY,
  EXAM_IDS,
  EXAMS,
  type ExamId,
  type ExamOutlook,
} from "./prepData";
import { closed, MISCONCEPTION_LABEL, proposedSet, readiness, type PrepModel, type PrepSub, type PrepTab } from "./prepModel";
import { StateGlyph } from "./SkillGraph";
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
    ielts: { readiness: series.ielts.readiness, forecast: series.ielts.forecast },
  };
  const forecast = series.sat.forecast;
  const exams = requirements(programs, outlook);
  const list = milestones(programs);

  if (sub === "requirements") return <Requirements exams={exams} series={series} />;
  return <Now model={model} forecast={forecast} milestoneList={list} onGo={onGo} onOpenSet={onOpenSet} onAccept={onAccept} />;
}

/* ---------- Сейчас: the set in work and what closed last ---------- */

function Now({
  model,
  forecast,
  milestoneList,
  onGo,
  onOpenSet,
  onAccept,
}: {
  model: PrepModel;
  forecast: Date;
  milestoneList: ReturnType<typeof milestones>;
  onGo: (tab: PrepTab, sub?: PrepSub, exam?: ExamId) => void;
  onOpenSet: (setId: string, topic?: string) => void;
  onAccept: (setId: string) => void;
}) {
  const proposed = proposedSet(model);
  const current = model.currentSet ? setById(model.currentSet) : null;
  const report = model.reportFor ? setById(model.reportFor) : null;

  return (
    <div className={styles.canvasGrid}>
      <section className={`${styles.canvas} ${styles.wide}`} aria-label="Сет">
        {report ? (
          <>
            <header className={styles.canvasHead}>
              <h3>
                Сет {report.number} закрыт <Icon name="circle-check" size={18} className={styles.okIcon} />
              </h3>
            </header>
            <p className={styles.lead}>Хорошая работа — {report.title.toLowerCase()} теперь держатся.</p>
            <ul className={styles.plainList}>
              {report.skills.map((id) => (
                <li key={id}>
                  <StateGlyph state={model.states[id]} />
                  {skillById(id).name} — {STATE_LABEL[model.states[id]]}
                </li>
              ))}
              {report.skills
                .flatMap((id) => model.misconceptions[id])
                .filter((m) => m.status === "resolved")
                .map((m) => (
                  <li key={m.id}>
                    <Icon name="check" size={14} className={styles.okIcon} />
                    {m.text} — {MISCONCEPTION_LABEL(m)}
                  </li>
                ))}
            </ul>
          </>
        ) : (
          <header className={styles.canvasHead}>
            <h3>{current ? `Сейчас: сет ${current.number}` : "Маршрут"}</h3>
          </header>
        )}

        {current ? (
          <div className={styles.nextSet}>
            <span className={styles.muted}>до {formatDate(current.deadline)}</span>
            <strong>{current.title}</strong>
            <span>
              закрыто {closed(model, current)} из {current.skills.length}
            </span>
            <button type="button" className={styles.primary} onClick={() => onOpenSet(current.id)}>
              <Icon name="play" size={16} /> Продолжить
            </button>
          </div>
        ) : proposed ? (
          <div className={styles.nextSet}>
            <span className={styles.muted}>Следующий · до {formatDate(proposed.deadline)}</span>
            <strong>
              Сет {proposed.number}: {proposed.title}
            </strong>
            <span className={styles.muted}>{proposed.why}</span>
            <div className={styles.actions}>
              <button type="button" className={styles.primary} onClick={() => onAccept(proposed.id)}>
                Принять
              </button>
              <button type="button" className={styles.secondary} onClick={() => onGo("sets", "list")}>
                Выбрать другой
              </button>
            </div>
          </div>
        ) : (
          <p className={styles.muted}>Все сеты пройдены — осталось закрепление и тест.</p>
        )}
      </section>

      <PaceCard forecast={forecast} onGo={onGo} />
      <Important model={model} milestoneList={milestoneList} onGo={onGo} onOpenSet={onOpenSet} />
    </div>
  );
}

/**
 * Pace, in words, from Quack — the same verdict the Quack! screen shows, so the two never disagree.
 * No readiness percentages: the student needs to know whether they make it, not a number.
 */
function PaceCard({ forecast, onGo }: { forecast: Date; onGo: (tab: PrepTab, sub?: PrepSub) => void }) {
  const { state } = useQuack();
  const pace = state.standing?.pace;

  return (
    <section className={styles.canvas} aria-label="Темп">
      <header className={styles.canvasHead}>
        <h3>Темп</h3>
        <span className={styles.muted}>как в Quack</span>
      </header>
      {pace ? (
        <div className={styles.paceBox} data-pace={pace.level}>
          <div className={styles.paceHead}>
            <strong className={styles.paceVerdict}>{pace.verdict}</strong>
            <span className={styles.paceMeter} aria-hidden="true">
              {[0, 1, 2, 3].map((step) => (
                <span key={step} data-on={step <= pace.level} />
              ))}
            </span>
          </div>
          <p>{pace.summary}</p>
          {pace.advice[0] && <p className={styles.paceHint}>{pace.advice[0]}</p>}
        </div>
      ) : (
        // Demo programs are not saved, so Quack has nothing to judge: the forecast date alone
        <p className={styles.lead}>Прогноз готовности — {formatDate(forecast)}</p>
      )}
      <button type="button" className={styles.link} onClick={() => onGo("overview", "requirements")}>
        Требования и прогноз →
      </button>
    </section>
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

function Requirements({
  exams,
  series,
}: {
  exams: ReturnType<typeof requirements>;
  series: Record<ExamId, ReturnType<typeof forecastSeries>>;
}) {
  // A chart for every exam the knowledge model covers and the programs ask for
  const charted = EXAM_IDS.filter((id) => exams.some((e) => e.id === id && e.hasModel));

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
                <dd className={styles.chips}>
                  {exam.programs.map((p) => (
                    <span key={p.id}>{p.university}</span>
                  ))}
                </dd>
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

      {charted.map((id) => (
        <section key={id} className={`${styles.canvas} ${styles.full}`} aria-label={`Прогноз готовности ${EXAMS[id].name}`}>
          <header className={styles.canvasHead}>
            <h3>Готовность {EXAMS[id].name} и прогноз</h3>
            <span className={styles.muted}>факт — сплошная, прогноз — пунктир</span>
          </header>
          <ForecastChart points={series[id].points} testDate={EXAMS[id].test} forecast={series[id].forecast} />
        </section>
      ))}
    </div>
  );
}
