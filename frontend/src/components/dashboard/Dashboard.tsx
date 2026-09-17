"use client";

// Dashboard — the screen behind the Quack! button and the first thing a student sees.
// It merges the requirements of the saved programs, catches real-world conflicts and shows
// how the sections feed each other. Everything here is derived: nothing to fill in by hand.

import { useEffect, useMemo, useState } from "react";
import type { Profile } from "../choice/assistant";
import { Icon } from "../choice/Icon";
import { LevelBadge } from "../choice/ProgramUi";
import { evaluate, formatEur, programById } from "../choice/programs";
import { daysBetween, formatDate, formatShort, TODAY } from "../prep/prepData";
import { setById } from "../prep/prepData";
import { initialModel, proposedSet, readiness, reviveModel, type PrepTab } from "../prep/prepModel";
import { calendar, examLabel, hardConflicts, removalEffects, unionExams, watchList } from "./dashboardRules";
import styles from "./dashboard.module.css";

const WATCH_KEY = "quack-dashboard-watch";
const PREP_KEY = "quack-prep";

type Props = {
  saved: string[];
  profile: Profile;
  onUnsave: (id: string) => void;
  onOpenChoice: () => void;
  onOpenPrep: (tab: PrepTab) => void;
};

/** Readiness in «Подготовке» read as a forecast score, so the dashboard can react to it. */
const forecastScore = (percent: number) => Math.round((400 + percent * 4) / 10) * 10;

export function Dashboard({ saved, profile, onUnsave, onOpenChoice, onOpenPrep }: Props) {
  const [watched, setWatched] = useState<string[]>([]);
  const [resolved, setResolved] = useState<Record<string, string>>({});
  const [openEffect, setOpenEffect] = useState<string | null>(null);

  useEffect(() => {
    try {
      setWatched(JSON.parse(localStorage.getItem(WATCH_KEY) ?? "[]"));
    } catch {}
  }, []);

  const keepWatching = (id: string) => {
    const next = watched.includes(id) ? watched : [...watched, id];
    setWatched(next);
    try {
      localStorage.setItem(WATCH_KEY, JSON.stringify(next));
    } catch {}
  };

  // Preparation is a separate screen with its own storage; here we only read it
  const prep = useMemo(() => {
    try {
      return reviveModel(JSON.parse(localStorage.getItem(PREP_KEY) ?? "null")) ?? initialModel();
    } catch {
      return initialModel();
    }
  }, []);

  const programs = saved.map(programById).filter(Boolean);
  const exams = unionExams(programs);
  const conflicts = hardConflicts(programs, exams);
  const dates = calendar(programs, exams);
  const effects = removalEffects(programs, exams);
  const watch = watchList(programs, profile);

  const prepReadiness = readiness(prep);
  const predicted = forecastScore(prepReadiness);
  const current = prep.currentSet ? setById(prep.currentSet) : proposedSet(prep);

  if (!programs.length) {
    return (
      <div className={styles.dashboard}>
        <div className={styles.empty}>
          <h2>Здесь соберётся твой план</h2>
          <p>
            Сохрани программы в «Выборе» — и дашборд сам сведёт их требования в один список экзаменов, проверит даты на конфликты и
            наполнит «Подготовку». Нажимать «сформировать план» не нужно.
          </p>
          <button type="button" className={styles.primary} onClick={onOpenChoice}>
            Перейти к выбору
          </button>
        </div>
      </div>
    );
  }

  const openConflicts = conflicts.filter((c) => !resolved[c.id]);

  return (
    <div className={styles.dashboard}>
      <header className={styles.head}>
        <div>
          <h2 className={styles.title}>Дашборд</h2>
          <p className={styles.muted}>
            {programs.length} сохранённых · {exams.length} экзамена(ов) после объединения ·{" "}
            {openConflicts.length ? `${openConflicts.length} конфликт(а) требуют решения` : "конфликтов нет"}
          </p>
        </div>
        <button type="button" className={styles.secondary} onClick={onOpenChoice}>
          <Icon name="graduation-cap" size={16} /> Добавить программы
        </button>
      </header>

      <div className={styles.grid}>
        {/* 1. Union engine */}
        <section className={`${styles.card} ${styles.wide}`} aria-label="Что тебе сдавать">
          <header className={styles.cardHead}>
            <h3>Что тебе сдавать</h3>
            <span className={styles.muted}>требования {programs.length} программ сведены в один список</span>
          </header>
          <div className={styles.exams}>
            {exams.map((union) => (
              <article key={union.exam.id} className={styles.exam}>
                <div className={styles.examTop}>
                  <strong>{examLabel(union)}</strong>
                  <span className={styles.muted}>
                    один экзамен на {union.demands.length} программ{union.demands.length === 1 ? "у" : "ы"}
                  </span>
                </div>
                <ul className={styles.demands}>
                  {union.demands.map((d) => (
                    <li key={d.program.id} data-enough={d.enough}>
                      <span className={styles.dot} aria-hidden="true" />
                      <span>
                        <strong>{d.program.university}</strong> — {d.note}
                      </span>
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
          <p className={styles.footNote}>
            Планка всегда по самой высокой: тянем до неё, но видно, кому хватает меньшего. Один и тот же экзамен не сдаётся дважды.
          </p>
        </section>

        {/* 2. Conflicts */}
        <section className={`${styles.card} ${openConflicts.length ? styles.alert : ""}`} aria-label="Конфликты">
          <header className={styles.cardHead}>
            <h3>
              <Icon name="triangle-alert" size={18} /> Конфликты
            </h3>
          </header>
          {openConflicts.length === 0 ? (
            <p className={styles.muted}>Даты тестов, дедлайны и раунды подачи сходятся.</p>
          ) : (
            <ul className={styles.conflicts}>
              {openConflicts.map((c) => (
                <li key={c.id}>
                  <p>{c.text}</p>
                  <div className={styles.actions}>
                    {c.options.map((o) => (
                      <button
                        key={o}
                        type="button"
                        className={styles.secondary}
                        onClick={() => setResolved((r) => ({ ...r, [c.id]: o }))}
                      >
                        {o}
                      </button>
                    ))}
                  </div>
                </li>
              ))}
            </ul>
          )}
          {Object.entries(resolved).map(([id, choice]) => (
            <p key={id} className={styles.resolved}>
              <Icon name="check" size={14} /> {choice}
            </p>
          ))}
        </section>

        {/* 3. Preparation filled itself */}
        <section className={styles.card} aria-label="Подготовка">
          <header className={styles.cardHead}>
            <h3>Подготовка собралась сама</h3>
          </header>
          <p className={styles.muted}>Как только появилась первая сохранённая программа, раздел наполнился без кнопок.</p>
          <dl className={styles.facts}>
            <div>
              <dt>Экзамены</dt>
              <dd>{exams.map((u) => u.exam.name).join(", ")}</dd>
            </div>
            <div>
              <dt>Готовность</dt>
              <dd>
                {prepReadiness}% · прогноз SAT Math ≈ {predicted}
              </dd>
            </div>
            {current && (
              <div>
                <dt>Сет</dt>
                <dd>
                  {prep.currentSet ? "текущий" : "предложен"}: {current.title}, до {formatDate(current.deadline)}
                </dd>
              </div>
            )}
          </dl>
          <button type="button" className={styles.primary} onClick={() => onOpenPrep("overview")}>
            Открыть подготовку
          </button>
        </section>

        {/* Calendar */}
        <section className={styles.card} aria-label="Ближайшие даты">
          <header className={styles.cardHead}>
            <h3>Ближайшие даты</h3>
            <span className={styles.muted}>из требований, а не вручную</span>
          </header>
          <ol className={styles.dates}>
            {dates.slice(0, 5).map((m) => (
              <li key={`${m.title}-${m.date.getTime()}`}>
                <span className={styles.date}>{formatShort(m.date)}</span>
                <span>
                  <strong>{m.title}</strong>
                  <span className={styles.muted}> · {m.detail}</span>
                </span>
                <span className={styles.muted}>{daysBetween(TODAY, m.date)} дн.</span>
              </li>
            ))}
          </ol>
        </section>

        {/* 4. Two-way link */}
        <section className={`${styles.card} ${styles.wide}`} aria-label="Связь в обе стороны">
          <header className={styles.cardHead}>
            <h3>Связь в обе стороны</h3>
            <span className={styles.muted}>что изменится, если тронуть сохранённые</span>
          </header>

          <ul className={styles.effects}>
            {effects.map((e) => {
              const { level } = evaluate(e.program, profile);
              const mathNeed = e.program.satMin ? Math.round(e.program.satMin / 2 / 10) * 10 : undefined;
              return (
                <li key={e.program.id}>
                  <button type="button" className={styles.effectHead} onClick={() => setOpenEffect((id) => (id === e.program.id ? null : e.program.id))}>
                    <span>
                      <strong>{e.program.university}</strong>
                      <span className={styles.muted}>
                        {" "}
                        · подача {e.program.deadline} · {formatEur(e.program.costEur)}
                      </span>
                    </span>
                    <LevelBadge level={level} />
                  </button>

                  {mathNeed !== undefined && (
                    <p className={styles.prognosis} data-ok={predicted >= mathNeed}>
                      Прогноз из подготовки {predicted} против {mathNeed} —{" "}
                      {predicted >= mathNeed
                        ? "по прогнозу проходишь, оценка поднимется после мока"
                        : `не хватает ${mathNeed - predicted}; закроешь сеты — оценка сама изменится`}
                    </p>
                  )}

                  {openEffect === e.program.id && (
                    <div className={styles.effectBody}>
                      {e.drops.length > 0 && (
                        <p>
                          Если убрать: {e.drops.join(", ")} больше никому не нужен и уйдёт из подготовки и календаря.{" "}
                          <span className={styles.muted}>Всё, что ты уже выучил, останется — вернёшь программу, ничего заново проходить не нужно.</span>
                        </p>
                      )}
                      {e.stays.map((line) => (
                        <p key={line}>{line}</p>
                      ))}
                      <button type="button" className={styles.danger} onClick={() => onUnsave(e.program.id)}>
                        <Icon name="trash-2" size={16} /> Убрать из сохранённых
                      </button>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        </section>

        {/* 5. Respect for the student's choice */}
        <section className={`${styles.card} ${styles.wide}`} aria-label="Под присмотром">
          <header className={styles.cardHead}>
            <h3>Под присмотром</h3>
            <span className={styles.muted}>профиль изменился — программы остаются на месте</span>
          </header>
          {watch.length === 0 ? (
            <p className={styles.muted}>Все сохранённые проходят по профилю и бюджету.</p>
          ) : (
            <ul className={styles.watch}>
              {watch.map((w) => (
                <li key={w.program.id}>
                  <div>
                    <strong>{w.program.university}</strong>
                    <span className={styles.muted}> · {w.program.program}</span>
                    <p className={styles.warnText}>Внимание: {w.reason}.</p>
                  </div>
                  {watched.includes(w.program.id) ? (
                    <span className={styles.kept}>
                      <Icon name="star" size={14} /> следим за стипендиями
                    </span>
                  ) : (
                    <div className={styles.actions}>
                      <button type="button" className={styles.secondary} onClick={() => keepWatching(w.program.id)}>
                        Оставить для стипендий
                      </button>
                      <button type="button" className={styles.danger} onClick={() => onUnsave(w.program.id)}>
                        Убрать
                      </button>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
          <p className={styles.footNote}>Сервис не удаляет сохранённое сам: решение всегда за тобой.</p>
        </section>
      </div>
    </div>
  );
}
