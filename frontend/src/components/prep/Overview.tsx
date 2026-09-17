"use client";

import { Icon } from "../choice/Icon";
import type { Program } from "../choice/programs";
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
  STATE_LABEL,
  TODAY,
} from "./prepData";
import { closed, MISCONCEPTION_LABEL, proposedSet, readiness, type PrepModel, type PrepTab } from "./prepModel";
import { StateGlyph } from "./SkillGraph";
import styles from "./prep.module.css";

type Props = {
  model: PrepModel;
  programs: Program[];
  onTab: (tab: PrepTab) => void;
  onAccept: (setId: string) => void;
  onToggleMilestone: (id: string) => void;
  onResolveConflict: (id: string, option: string) => void;
};

/** §4.1: requirements, milestones, progress and the set report; the next set is accepted here. */
export function Overview({ model, programs, onTab, onAccept, onToggleMilestone, onResolveConflict }: Props) {
  const now = readiness(model);
  const { points, forecast } = forecastSeries(now, model.extraDays);
  const exams = requirements(programs, forecast, now);
  const sat = exams.find((e) => e.id === "sat");
  const list = milestones(programs);
  const done = list.filter((m) => model.milestonesDone.includes(m.id)).length;
  const conflictList = conflicts(list);
  const proposed = proposedSet(model);
  const current = model.currentSet ? setById(model.currentSet) : null;
  const report = model.reportFor ? setById(model.reportFor) : null;

  return (
    <div className={styles.canvasGrid}>
      {/* Requirements */}
      {exams.map((exam) => {
        const margin = exam.testDate && exam.forecast ? daysBetween(exam.forecast, exam.testDate) : 0;
        return (
          <section key={exam.id} className={`${styles.canvas} ${styles.examCard}`} aria-label={exam.name}>
            <header className={styles.canvasHead}>
              <h3>{exam.name}</h3>
              <span className={styles.demoTag}>демо</span>
            </header>
            <div className={styles.examTarget}>
              <span className={styles.examTargetValue}>{exam.target}</span>
              <span className={styles.examTargetNote}>
                цель · {exam.targetNote}
              </span>
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
                <div className={styles.readinessRow}>
                  <span>Готовность</span>
                  <strong>{exam.readiness}%</strong>
                </div>
                <div className={styles.bar} role="progressbar" aria-valuenow={exam.readiness} aria-valuemin={0} aria-valuemax={100}>
                  <span style={{ width: `${exam.readiness}%` }} />
                </div>
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

      {/* Set report / next set */}
      <section className={`${styles.canvas} ${styles.reportCard}`} aria-label="Сет">
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
            <button type="button" className={styles.primary} onClick={() => onTab("current")}>
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
              <button type="button" className={styles.secondary} onClick={() => onTab("sets")}>
                Выбрать другой
              </button>
            </div>
          </div>
        ) : (
          <p className={styles.muted}>Все сеты пройдены — осталось закрепление и тест.</p>
        )}
      </section>

      {/* Forecast */}
      {sat && (
        <section className={`${styles.canvas} ${styles.wide}`} aria-label="Прогноз готовности">
          <header className={styles.canvasHead}>
            <h3>Готовность SAT Math и прогноз</h3>
            <span className={styles.muted}>факт — сплошная, прогноз — пунктир</span>
          </header>
          <ForecastChart points={points} testDate={sat.testDate!} forecast={forecast} />
        </section>
      )}

      {/* Realism + diagnostic */}
      <section className={`${styles.canvas} ${styles.sideCard}`} aria-label="Сохранённые программы">
        <header className={styles.canvasHead}>
          <h3>Сохранённые</h3>
          <span className={styles.muted}>оценки пересчитываются</span>
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

        <div className={styles.diagnostic}>
          <strong>Первичный замер · 3 сентября</strong>
          <p className={styles.muted}>
            Фундамент — линейные уравнения и подобие. Тригонометрия не держится, корень — свойства окружности. Начали с окружности и
            модуля.
          </p>
          <button type="button" className={styles.link} onClick={() => onTab("sets")}>
            Смотреть на карте навыков →
          </button>
        </div>
      </section>
      {/* Milestones */}
      <section className={`${styles.canvas} ${styles.wide}`} aria-label="Вехи">
        <header className={styles.canvasHead}>
          <h3>Вехи</h3>
          <span className={styles.muted}>
            сделано {done} из {list.length}
          </span>
        </header>

        {conflictList
          .filter((c) => !model.resolvedConflicts[c.id])
          .map((c) => (
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
