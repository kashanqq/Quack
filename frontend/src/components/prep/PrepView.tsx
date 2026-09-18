"use client";

// "Подготовка" (product-logic §4). Input of the section is the saved programs; with none saved the
// student can look at it on demo programs. Its state lives in localStorage until there is a backend.

import { FirstHint } from "@/components/hints/FirstHint";
import { useEffect, useRef, useState } from "react";
import { morph } from "@/components/transition/morph";
import { CurrentSet } from "./CurrentSet";
import { Overview } from "./Overview";
import { savedPrograms, setById, type ExamId } from "./prepData";
import {
  acceptSet,
  initialModel,
  makeCurrent,
  reviveModel,
  subFor,
  type PrepModel,
  type PrepSub,
  type PrepTab,
} from "./prepModel";
import { quackSource } from "../quack/source";
import { SetsView } from "./SetsView";
import styles from "./prep.module.css";

const STORAGE_KEY = "quack-prep";

type Props = {
  tab: PrepTab;
  onTab: (tab: PrepTab) => void;
  sub: PrepSub;
  onSub: (sub: PrepSub) => void;
  saved: string[];
  onGoToChoice: () => void;
};

export function PrepView({ tab, onTab, sub, onSub, saved, onGoToChoice }: Props) {
  // Rendered only after the student switches to the section, so storage can be read right away
  const [model, setModel] = useState<PrepModel>(() => {
    try {
      return reviveModel(JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null")) ?? initialModel();
    } catch {
      return initialModel();
    }
  });
  const [toast, setToast] = useState<string | null>(null);
  // Which exam the route, the map and the set list show; starts on the exam of the set in work
  const [exam, setExam] = useState<ExamId>(() => (model.currentSet ? setById(model.currentSet).exam : "sat"));
  const scrollRef = useRef<HTMLDivElement>(null);

  // A sub-tab belongs to its tab; switching tabs falls back to the first one
  const current = subFor(tab, sub);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(model));
    } catch {}
    // Preparation is a source of truth for Quack: an answer, a passed set or a ticked date is recomputed at once
    quackSource().report({ prep: model });
  }, [model]);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 3200);
    return () => clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: 0 });
  }, [tab, current]);

  const programs = savedPrograms(saved, model.demo);

  /** One move for both levels, so a jump across the section is a single animated step */
  const go = (next: PrepTab, nextSub?: PrepSub, nextExam?: ExamId) =>
    morph(() => {
      onTab(next);
      if (nextSub) onSub(nextSub);
      if (nextExam) setExam(nextExam);
    });

  const accept = (id: string) => {
    setModel((m) => acceptSet(m, id));
    setToast("Сет принят — он в «Текущем сете»");
    go("current", "check", setById(id).exam);
  };

  const choose = (id: string) => {
    const { model: next, shift } = makeCurrent(model, id);
    setModel(next);
    setToast(shift ? `Сет выбран не по порядку маршрута — прогноз сдвинулся на ${shift} дн.` : "Текущий сет сменён");
  };

  return (
    <div className={styles.prep}>
      <header className={styles.prepHead}>
        <div>
          <h2 className={styles.prepTitle}>Подготовка</h2>
          <p className={styles.muted}>
            {programs.length
              ? `По ${saved.length ? "сохранённым " : "демо-"}программам: ${programs.map((p) => p.university).join(", ")}`
              : "Вход раздела — сохранённые программы"}
          </p>
        </div>
      </header>

      <div className={styles.prepScroll} ref={scrollRef}>
        {programs.length === 0 ? (
          <div className={styles.emptyCanvas}>
            <h3>Сначала сохрани программы</h3>
            <p className={styles.muted}>
              Из сохранённых программ выводятся требования: какие экзамены и на какой балл. Из требований — вехи и маршрут из сетов.
            </p>
            <div className={styles.actions}>
              <button type="button" className={styles.primary} onClick={onGoToChoice}>
                Перейти к выбору
              </button>
              <button type="button" className={styles.secondary} onClick={() => setModel((m) => ({ ...m, demo: true }))}>
                Посмотреть на демо-программах
              </button>
            </div>
          </div>
        ) : (
          <>
            {saved.length ? (
              <FirstHint id="prep" title="Зачем «Подготовка»">
                Здесь план подготовки к экзаменам, которые требуют твои программы. Начни с «Сейчас»: там темп и что сделать первым.
                Потом в «Текущем сете» проверяй себя: каждый верный ответ красит навык на карте. Ассистент там же соберёт план к твоей дате. Разделы слева.
              </FirstHint>
            ) : (
              <FirstHint id="prep-demo" title="Это пример" action={{ label: "Перейти к выбору", onClick: onGoToChoice }}>
                План собран на демо-программах. Сохрани свои в «Выборе», и подготовка пересоберётся под их экзамены и сроки.
              </FirstHint>
            )}
            {/* Tabs and their parts are picked only in the left column — on phones it is the menu drawer */}
            <div key={`${tab}-${current}`} className={styles.tabBody}>
              {tab === "overview" && (
                <Overview
                  model={model}
                  programs={programs}
                  sub={current}
                  onGo={go}
                  onAccept={accept}
                  onToggleMilestone={(id) =>
                    setModel((m) => ({
                      ...m,
                      milestonesDone: m.milestonesDone.includes(id) ? m.milestonesDone.filter((x) => x !== id) : [...m.milestonesDone, id],
                    }))
                  }
                  onResolveConflict={(id, option) => {
                    setModel((m) => ({ ...m, resolvedConflicts: { ...m.resolvedConflicts, [id]: option } }));
                    setToast("Решение принято — вехи пересобраны");
                  }}
                />
              )}
              {tab === "sets" && (
                <SetsView model={model} sub={current} exam={exam} onExam={setExam} onMakeCurrent={choose} onModel={setModel} />
              )}
              {tab === "current" && (
                <CurrentSet
                  model={model}
                  sub={current}
                  onModel={setModel}
                  onAccept={accept}
                  onGo={go}
                  onToast={setToast}
                />
              )}
            </div>
          </>
        )}
      </div>

      {toast && (
        <div className={styles.toast} role="status">
          {toast}
        </div>
      )}
    </div>
  );
}
