"use client";

// Dashboard — the screen behind the Quack! button and the first thing a student sees.
// The saved programs are its input; the work is split across GitHub-style tabs so the screen
// says where to look: a short overview, the merged exams, the calendar and the programs.

import { useEffect, useMemo, useState } from "react";
import type { Profile } from "../choice/assistant";
import { Icon } from "../choice/Icon";
import { programById } from "../choice/programs";
import { daysBetween, formatDate, setById, TODAY } from "../prep/prepData";
import { initialModel, proposedSet, readiness, reviveModel, type PrepTab } from "../prep/prepModel";
import { ActivityGrid } from "./ActivityGrid";
import { CalendarTab } from "./CalendarTab";
import {
  activityByDay,
  calendarEvents,
  DASH_TABS,
  hardConflicts,
  removalEffects,
  unionExams,
  watchList,
  type DashTab,
} from "./dashboardRules";
import { ExamsTab } from "./ExamsTab";
import { ProgramsTab } from "./ProgramsTab";
import styles from "./dashboard.module.css";

const WATCH_KEY = "quack-dashboard-watch";
const PREP_KEY = "quack-prep";

type Props = {
  /** The open category; the left column switches it too */
  tab: DashTab;
  onTab: (tab: DashTab) => void;
  saved: string[];
  profile: Profile;
  /** Chat history, used for the activity grid */
  chatDays: number[];
  onUnsave: (id: string) => void;
  onOpenChoice: () => void;
  onOpenPrep: (tab: PrepTab) => void;
};

/** Readiness in «Подготовке» read as a forecast score, so the dashboard can react to it. */
const forecastScore = (percent: number) => Math.round((400 + percent * 4) / 10) * 10;

export function Dashboard({ tab, onTab, saved, profile, chatDays, onUnsave, onOpenChoice, onOpenPrep }: Props) {
  const [watched, setWatched] = useState<string[]>([]);
  const [resolved, setResolved] = useState<Record<string, string>>({});

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
  const conflicts = hardConflicts(programs, exams).filter((c) => !resolved[c.id]);
  const events = calendarEvents(programs, exams);
  const next = events.find((e) => e.date >= TODAY);

  const prepReadiness = readiness(prep);
  const predicted = forecastScore(prepReadiness);
  const currentSet = prep.currentSet ? setById(prep.currentSet) : proposedSet(prep);
  const activity = useMemo(() => activityByDay(Object.values(prep.evidence).flat(), chatDays), [prep, chatDays]);

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

  return (
    <div className={styles.dashboard}>
      <header className={styles.head}>
        <div>
          <h2 className={styles.title}>Дашборд</h2>
          <p className={styles.muted}>Всё, что следует из твоих сохранённых программ</p>
        </div>
        <button type="button" className={styles.secondary} onClick={onOpenChoice}>
          <Icon name="graduation-cap" size={16} /> Добавить программы
        </button>
      </header>

      <nav className={styles.tabs} role="tablist" aria-label="Разделы дашборда">
        {DASH_TABS.map((t) => (
          <button key={t.tab} type="button" role="tab" aria-selected={tab === t.tab} onClick={() => onTab(t.tab)}>
            <Icon name={t.icon} size={16} />
            {t.label}
            {t.tab === "exams" && <span className={styles.counter}>{exams.length}</span>}
            {t.tab === "calendar" && <span className={styles.counter}>{events.length}</span>}
            {t.tab === "programs" && <span className={styles.counter}>{programs.length}</span>}
          </button>
        ))}
      </nav>

      <div key={tab} className={styles.tabBody}>
        {tab === "overview" && (
          <div className={styles.grid}>
            <section className={`${styles.card} ${styles.wide}`} aria-label="Коротко">
              <div className={styles.tiles}>
                <button type="button" className={styles.tile} onClick={() => onTab("exams")}>
                  <span className={styles.tileValue}>{exams.length}</span>
                  <span className={styles.muted}>экзамена после объединения</span>
                </button>
                <button type="button" className={styles.tile} onClick={() => onTab("calendar")}>
                  <span className={styles.tileValue}>{next ? daysBetween(TODAY, next.date) : "—"}</span>
                  <span className={styles.muted}>дней до ближайшей даты{next ? `: ${next.title.toLowerCase()}` : ""}</span>
                </button>
                <button type="button" className={styles.tile} data-alert={conflicts.length > 0} onClick={() => onTab("calendar")}>
                  <span className={styles.tileValue}>{conflicts.length}</span>
                  <span className={styles.muted}>конфликтов в датах и раундах</span>
                </button>
                <button type="button" className={styles.tile} onClick={() => onOpenPrep("overview")}>
                  <span className={styles.tileValue}>{prepReadiness}%</span>
                  <span className={styles.muted}>готовность · прогноз ≈ {predicted}</span>
                </button>
              </div>
            </section>

            <section className={`${styles.card} ${conflicts.length ? styles.alert : ""}`} aria-label="Конфликты">
              <header className={styles.cardHead}>
                <h3>
                  <Icon name="triangle-alert" size={18} /> Конфликты
                </h3>
              </header>
              {conflicts.length === 0 ? (
                <p className={styles.muted}>Даты тестов, дедлайны и раунды подачи сходятся.</p>
              ) : (
                <ul className={styles.conflicts}>
                  {conflicts.map((c) => (
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
                {currentSet && (
                  <div>
                    <dt>Сет</dt>
                    <dd>
                      {prep.currentSet ? "текущий" : "предложен"}: {currentSet.title}, до {formatDate(currentSet.deadline)}
                    </dd>
                  </div>
                )}
              </dl>
              <button type="button" className={styles.primary} onClick={() => onOpenPrep("overview")}>
                Открыть подготовку
              </button>
            </section>

            <div className={styles.wide}>
              <ActivityGrid days={activity} />
            </div>
          </div>
        )}

        {tab === "exams" && <ExamsTab exams={exams} programCount={programs.length} />}
        {tab === "calendar" && <CalendarTab events={events} />}
        {tab === "programs" && (
          <ProgramsTab
            effects={removalEffects(programs, exams)}
            watch={watchList(programs, profile)}
            profile={profile}
            predicted={predicted}
            watched={watched}
            onWatch={keepWatching}
            onUnsave={onUnsave}
          />
        )}
      </div>
    </div>
  );
}
