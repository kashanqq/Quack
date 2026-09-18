"use client";

import { Icon } from "../choice/Icon";
import type { Program } from "../choice/programs";
import { useQuack } from "../quack/source";
import { routeDelay } from "../quack/standing";
import { ForecastChart } from "./ForecastChart";
import {
  conflicts,
  daysBetween,
  formatDate,
  formatShort,
  forecastSeries,
  milestones,
  realismShift,
  requirements,
  setById,
  skillById,
  SKILLS,
  STATE_LABEL,
  TODAY,
} from "./prepData";
import { closed, MISCONCEPTION_LABEL, proposedSet, readiness, type PrepModel, type PrepSub, type PrepTab } from "./prepModel";
import { StateGlyph } from "./SkillGraph";
import styles from "./prep.module.css";

type Props = {
  model: PrepModel;
  programs: Program[];
  sub: PrepSub;
  /** Jump to another tab, optionally straight to one of its sub-tabs */
  onGo: (tab: PrepTab, sub?: PrepSub) => void;
  onAccept: (setId: string) => void;
  onToggleMilestone: (id: string) => void;
  onResolveConflict: (id: string, option: string) => void;
};

/**
 * §4.1 — the section's overview, split into four sub-tabs so one screen answers one question:
 * what to do now, what the programs demand, which dates are coming, how the programs are changing.
 */
export function Overview({ model, programs, sub, onGo, onAccept, onToggleMilestone, onResolveConflict }: Props) {
  const now = readiness(model);
  const { points, forecast } = forecastSeries(now, model.extraDays);
  const exams = requirements(programs, forecast, now);
  const list = milestones(programs);

  if (sub === "requirements") return <Requirements exams={exams} points={points} forecast={forecast} />;
  if (sub === "milestones")
    return (
      <Milestones
        list={list}
        conflictList={conflicts(list)}
        model={model}
        onToggleMilestone={onToggleMilestone}
        onResolveConflict={onResolveConflict}
      />
    );
  if (sub === "programs") return <Programs programs={programs} onGo={onGo} />;
  return <Now model={model} forecast={forecast} milestoneList={list} onGo={onGo} onAccept={onAccept} />;
}

/* ---------- Сейчас: the set in work and what closed last ---------- */

function Now({
  model,
  forecast,
  milestoneList,
  onGo,
  onAccept,
}: {
  model: PrepModel;
  forecast: Date;
  milestoneList: ReturnType<typeof milestones>;
  onGo: (tab: PrepTab, sub?: PrepSub) => void;
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
            <button type="button" className={styles.primary} onClick={() => onGo("current")}>
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
              <button type="button" className={styles.secondary} onClick={() => onGo("sets")}>
                Выбрать другой
              </button>
            </div>
          </div>
        ) : (
          <p className={styles.muted}>Все сеты пройдены — осталось закрепление и тест.</p>
        )}
      </section>

      <PaceCard forecast={forecast} onGo={onGo} />
      <Important model={model} milestoneList={milestoneList} onGo={onGo} />
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
}: {
  model: PrepModel;
  milestoneList: ReturnType<typeof milestones>;
  onGo: (tab: PrepTab, sub?: PrepSub) => void;
}) {
  const items: { key: string; tone: "root" | "trap" | "late" | "date"; title: string; text: string; go: () => void; action: string }[] = [];

  for (const root of SKILLS.filter((s) => s.root && model.states[s.id] !== "solid")) {
    const above = SKILLS.filter((s) => s.requires.includes(root.id)).map((s) => s.name.toLowerCase());
    items.push({
      key: `root-${root.id}`,
      tone: "root",
      title: `Корень: ${root.name}`,
      text: above.length ? `из-за него ошибки в теме «${above.join("», «")}»` : "из-за него ошибки выше по карте",
      go: () => onGo("sets", "map"),
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
      go: () => onGo("current", "tasks"),
      action: "Задачи",
    });
  }

  const delay = routeDelay(model);
  if (delay) {
    items.push({
      key: "late",
      tone: "late",
      title: `Сет ${delay.set.number} ещё открыт`,
      text: `срок был ${formatDate(delay.set.deadline)} — прогноз сдвинулся на ${delay.days} дн.`,
      go: () => onGo("current"),
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
      go: () => onGo("overview", "milestones"),
      action: "Вехи",
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
  points,
  forecast,
}: {
  exams: ReturnType<typeof requirements>;
  points: ReturnType<typeof forecastSeries>["points"];
  forecast: Date;
}) {
  const sat = exams.find((e) => e.id === "sat");

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
              <p className={styles.muted}>Без модели знаний: подготовка идёт окнами на вехах, прогноза нет.</p>
            )}
          </section>
        );
      })}

      {sat && (
        <section className={`${styles.canvas} ${styles.full}`} aria-label="Прогноз готовности">
          <header className={styles.canvasHead}>
            <h3>Готовность SAT Math и прогноз</h3>
            <span className={styles.muted}>факт — сплошная, прогноз — пунктир</span>
          </header>
          <ForecastChart points={points} testDate={sat.testDate!} forecast={forecast} />
        </section>
      )}
    </div>
  );
}

/* ---------- Вехи: the dates, and the conflicts between them ---------- */

function Milestones({
  list,
  conflictList,
  model,
  onToggleMilestone,
  onResolveConflict,
}: {
  list: ReturnType<typeof milestones>;
  conflictList: ReturnType<typeof conflicts>;
  model: PrepModel;
  onToggleMilestone: (id: string) => void;
  onResolveConflict: (id: string, option: string) => void;
}) {
  const done = list.filter((m) => model.milestonesDone.includes(m.id)).length;
  const open = conflictList.filter((c) => !model.resolvedConflicts[c.id]);

  return (
    <div className={styles.canvasGrid}>
      {open.length > 0 && (
        <section className={`${styles.canvas} ${styles.full}`} aria-label="Конфликты вех">
          <header className={styles.canvasHead}>
            <h3>
              <Icon name="triangle-alert" size={18} /> Требуют решения
            </h3>
          </header>
          {open.map((c) => (
            <div key={c.id} className={styles.conflict} role="alert">
              <Icon name="triangle-alert" size={18} />
              <div>
                <p>{c.text}</p>
                <div className={styles.actions}>
                  {c.options.map((o) => (
                    <button key={o} type="button" className={styles.secondary} onClick={() => onResolveConflict(c.id, o)}>
                      {o}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </section>
      )}

      <section className={`${styles.canvas} ${styles.full}`} aria-label="Вехи">
        <header className={styles.canvasHead}>
          <h3>Вехи</h3>
          <span className={styles.muted}>
            сделано {done} из {list.length}
          </span>
        </header>

        <ol className={styles.timeline}>
          {list.map((m) => {
            const isDone = model.milestonesDone.includes(m.id);
            const left = daysBetween(TODAY, m.date);
            return (
              <li key={m.id} className={`${styles.milestone} ${isDone ? styles.milestoneDone : ""}`}>
                <span className={styles.milestoneDate}>
                  {formatShort(m.date)}
                  <span>{left > 0 ? `через ${left} дн.` : "сегодня"}</span>
                </span>
                <span className={styles.milestoneDot} aria-hidden="true" />
                <span className={styles.milestoneBody}>
                  <strong>{m.title}</strong>
                  <span className={styles.muted}>
                    {m.detail} · {m.source}
                  </span>
                </span>
                {m.checkable && (
                  <label className={styles.check}>
                    <input type="checkbox" checked={isDone} onChange={() => onToggleMilestone(m.id)} />
                    <span>{isDone ? "сделано" : "отметить"}</span>
                  </label>
                )}
              </li>
            );
          })}
        </ol>
        {Object.values(model.resolvedConflicts).map((choice) => (
          <p key={choice} className={styles.muted}>
            Выбрано: {choice}. Вехи пересобраны.
          </p>
        ))}
      </section>
    </div>
  );
}

/* ---------- Программы: how preparation moves the saved programs ---------- */

function Programs({ programs, onGo }: { programs: Program[]; onGo: (tab: PrepTab, sub?: PrepSub) => void }) {
  return (
    <div className={styles.canvasGrid}>
      <section className={`${styles.canvas} ${styles.wide}`} aria-label="Сохранённые программы">
        <header className={styles.canvasHead}>
          <h3>Сохранённые</h3>
          <span className={styles.muted}>оценки пересчитываются по ходу подготовки</span>
        </header>
        <ul className={styles.plainList}>
          {realismShift(programs).map(({ program, basis, change }) => (
            <li key={program.id} className={styles.realism}>
              <strong>{program.university}</strong>
              <span className={styles.muted}>
                {program.program} · {basis}
              </span>
              {change && (
                <span className={styles.shift}>
                  {change.from} → <b>{change.to}</b>
                  <span className={styles.muted}> · {change.reason}</span>
                </span>
              )}
            </li>
          ))}
        </ul>
      </section>

      <section className={styles.canvas} aria-label="Первичный замер">
        <header className={styles.canvasHead}>
          <h3>Первичный замер</h3>
          <span className={styles.muted}>3 сентября</span>
        </header>
        <p className={styles.muted}>
          Фундамент — линейные уравнения и подобие. Тригонометрия не держится, корень — свойства окружности. Начали с окружности и модуля.
        </p>
        <button
          type="button"
          className={styles.link}
          onClick={() => onGo("sets", "map")}
        >
          Смотреть на карте навыков →
        </button>
      </section>
    </div>
  );
}
