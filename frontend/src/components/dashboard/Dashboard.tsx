"use client";

// Обзор — the screen behind the Quack! button and the first thing a student sees.
// The saved programs are its input; the work is split across GitHub-style tabs so the screen
// says where to look: the main numbers and activity, the merged exams, the calendar and the programs.

import { useEffect, useMemo, useState } from "react";
import type { Profile } from "../choice/assistant";
import { Icon } from "../choice/Icon";
import { programById } from "../choice/programs";
import { initialModel, readiness, reviveModel, type PrepTab } from "../prep/prepModel";
import type { Signal } from "../quack/contract";
import { useQuack } from "../quack/source";
import { forecastScore } from "../quack/standing";
import { ActivityGrid } from "./ActivityGrid";
import { CalendarTab } from "./CalendarTab";
import { ChancesCard } from "./ChancesCard";
import { ChangesFeed } from "./ChangesFeed";
import {
  activityByDay,
  calendarEvents,
  DASH_TABS,
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

export function Dashboard({ tab, onTab, saved, profile, chatDays, onUnsave, onOpenChoice, onOpenPrep }: Props) {
  const [watched, setWatched] = useState<string[]>([]);
  const { state: quack } = useQuack();

  // Fresh signals turn into history a moment after Quack opens; for this visit they still read as new
  const [visitNew, setVisitNew] = useState<Set<string>>(() => new Set());
  const keyOf = (s: Signal) => `${s.id}@${s.at}`;
  const freshKey = quack.fresh.map(keyOf).join("|");
  useEffect(() => {
    if (freshKey) setVisitNew((seen) => new Set([...seen, ...freshKey.split("|")]));
  }, [freshKey]);

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
  const events = calendarEvents(programs, exams);
  const predicted = forecastScore(readiness(prep));
  const activity = useMemo(() => activityByDay(Object.values(prep.evidence).flat(), chatDays), [prep, chatDays]);

  if (!programs.length) {
    return (
      <div className={styles.dashboard}>
        <div className={styles.empty}>
          <h2>Здесь соберётся твой план</h2>
          <p>
            Сохрани программы в «Выборе» — и обзор сам сведёт их требования в один список экзаменов, проверит даты на конфликты и
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
          <h2 className={styles.title}>Обзор</h2>
          <p className={styles.muted}>Всё, что следует из твоих сохранённых программ</p>
        </div>
        <button type="button" className={styles.secondary} onClick={onOpenChoice}>
          <Icon name="graduation-cap" size={16} /> Добавить программы
        </button>
      </header>

      <nav className={styles.tabs} role="tablist" aria-label="Разделы обзора">
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
            {quack.standing && (
              <ChancesCard
                standing={quack.standing}
                fresh={quack.fresh}
                onOpenPrep={() => onOpenPrep("overview")}
                onOpenCalendar={() => onTab("calendar")}
                onOpenPrograms={() => onTab("programs")}
              />
            )}
            <ChangesFeed
              fresh={quack.fresh}
              history={quack.history}
              isNew={(s) => visitNew.has(keyOf(s))}
              onTarget={(target) => (target === "prep" ? onOpenPrep("overview") : target === "calendar" ? onTab("calendar") : onTab("programs"))}
            />
            <ActivityGrid days={activity} />
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
