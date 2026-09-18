"use client";

// "Подготовка" (product-logic §4). Input of the section is the saved programs; with none saved the
// student can look at it on demo programs. Its state is kept in the student's store (account/store.ts).

import { FirstHint } from "@/components/hints/FirstHint";
import { useEffect, useRef, useState } from "react";
import { morph } from "@/components/transition/morph";
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
import { store } from "../account/store";

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
  const [model, setModel] = useState<PrepModel>(() => reviveModel(store.get(STORAGE_KEY)) ?? initialModel());
  const [toast, setToast] = useState<string | null>(null);
  // Which exam the route, the map and the set list show; starts on the exam of the set in work
  const [exam, setExam] = useState<ExamId>(() => (model.currentSet ? setById(model.currentSet).exam : "sat"));
  // The set opened on «Сеты»: its graph and topics replace the list until the student goes back
  const [openSet, setOpenSet] = useState<{ id: string; topic?: string } | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // A sub-tab belongs to its tab; switching tabs falls back to the first one
  const current = subFor(tab, sub);

  useEffect(() => {
    store.set(STORAGE_KEY, model);
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
  }, [tab, current, openSet?.id]);

  const programs = savedPrograms(saved, model.demo);
  // An open set, the route and the map are drawings: they take all the height left
  const setOpen = programs.length > 0 && tab === "sets" && current === "list" && !!openSet;
  const fill = setOpen || (programs.length > 0 && tab === "sets" && (current === "route" || current === "map"));

  /** One move for both levels, so a jump across the section is a single animated step */
  const go = (next: PrepTab, nextSub?: PrepSub, nextExam?: ExamId) =>
    morph(() => {
      onTab(next);
      if (nextSub) onSub(nextSub);
      if (nextExam) setExam(nextExam);
    });

  /** Straight into a set's graph, from anywhere in the section */
  const openSetAt = (id: string | null, topic?: string) =>
    morph(() => {
      setOpenSet(id ? { id, topic } : null);
      if (!id) return;
      onTab("sets");
      onSub("list");
      setExam(setById(id).exam);
    });

  const accept = (id: string) => {
    setModel((m) => acceptSet(m, id));
    setToast("Сет принят — начни с первой темы на графе");
    openSetAt(id);
  };

  const choose = (id: string) => {
    const { model: next, shift } = makeCurrent(model, id);
    setModel(next);
    setToast(shift ? `Сет выбран не по порядку маршрута — прогноз сдвинулся на ${shift} дн.` : "Текущий сет сменён");
  };

  return (
    <div className={styles.prep}>
      {/* No section title: the column already says «Подготовка», the room goes to the work itself */}
      <div className={styles.prepScroll} ref={scrollRef} data-fill={fill || undefined}>
        {programs.length === 0 ? (
          <div className={styles.emptyCanvas}>
            <h3>Сначала сохрани программы</h3>
            <p className={styles.muted}>
              Из сохранённых программ выводятся требования: какие экзамены и на какой балл. Из требований — маршрут из сетов с дедлайнами.
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
            {setOpen ? null : saved.length ? (
              <FirstHint id="prep" title="Зачем «Подготовка»">
                Здесь план подготовки к экзаменам, которые требуют твои программы. В «Сетах» сверху три, которые мы советуем по твоим
                ошибкам. Внутри сета — граф тем до дедлайна: в каждой теме материал, проверка и ассистент.
              </FirstHint>
            ) : (
              <FirstHint id="prep-demo" title="Это пример" action={{ label: "Перейти к выбору", onClick: onGoToChoice }}>
                План собран на демо-программах. Сохрани свои в «Выборе», и подготовка пересоберётся под их экзамены и сроки.
              </FirstHint>
            )}
            {/* Tabs and their parts are picked only in the left column — on phones it is the menu drawer */}
            <div key={`${tab}-${current}-${openSet?.id ?? ""}`} className={styles.tabBody}>
              {tab === "overview" && (
                <Overview
                  model={model}
                  programs={programs}
                  sub={current}
                  onGo={go}
                  onOpenSet={openSetAt}
                  onAccept={accept}
                />
              )}
              {tab === "sets" && (
                <SetsView
                  model={model}
                  sub={current}
                  exam={exam}
                  onExam={setExam}
                  onMakeCurrent={choose}
                  onModel={setModel}
                  openSet={openSet}
                  onOpenSet={openSetAt}
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
