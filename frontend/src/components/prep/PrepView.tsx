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
import { Icon } from "../choice/Icon";
import { SetsView } from "./SetsView";
import { DiagnosticMock } from "./DiagnosticMock";
import type { DiagnosticResultSummary } from "./diagnosticData";
import styles from "./prep.module.css";
import { store } from "../account/store";

const STORAGE_KEY = "quack-prep";

/** One first-visit note per part of the section: what it shows and what to press. The ids are kept once seen. */
const INTROS: Record<PrepSub | "set", { id: string; title: string; text: string }> = {
  now: {
    id: "prep",
    title: "Зачем «Подготовка»",
    text: "Здесь план подготовки к экзаменам, которые требуют твои программы. «Сейчас» — главное на сегодня: какой сет в работе, что сделать дальше и успеваешь ли к тесту.",
  },
  requirements: {
    id: "prep-requirements",
    title: "Что такое «Требования»",
    text: "Какие экзамены и на какой балл нужны сохранённым программам, и когда ты, по прогнозу, будешь готов. Цели пересчитываются, когда меняется список программ.",
  },
  route: {
    id: "prep-route-v2",
    title: "Что такое маршрут",
    text: "Сет — несколько связанных тем с общим дедлайном. Ассистент собирает сеты под тебя по твоим ошибкам и пересобирает их, пока ты продвигаешься. Работаешь над одним — сменить можно в любой момент кнопкой «Сменить на этот», прогресс по темам не теряется.",
  },
  map: {
    id: "prep-map",
    title: "Как читать карту навыков",
    text: "Каждая карточка — сет, внутри его темы и как они держатся. Стрелка ведёт к сету, который опирается на предыдущий. Нажми на сет — справа его темы, а по теме — почему она в таком состоянии.",
  },
  set: {
    id: "prep-set",
    title: "Внутри сета",
    text: "Темы сета на шкале до его дедлайна, у каждой свой срок. Нажми на тему — откроется чат с ассистентом, который начинает с короткого материала, и мок-тест рядом. Ответы в тесте сразу меняют состояние темы.",
  },
};

type Props = {
  tab: PrepTab;
  onTab: (tab: PrepTab) => void;
  sub: PrepSub;
  onSub: (sub: PrepSub) => void;
  saved: string[];
  onGoToChoice: () => void;
  externalOpenDiagnostic?: boolean;
  onCloseExternalDiagnostic?: () => void;
  onDiagnosticStatusChange?: (done: boolean) => void;
};

export function PrepView({
  tab,
  onTab,
  sub,
  onSub,
  saved,
  onGoToChoice,
  externalOpenDiagnostic,
  onCloseExternalDiagnostic,
  onDiagnosticStatusChange,
}: Props) {
  // Rendered only after the student switches to the section, so storage can be read right away
  const [model, setModel] = useState<PrepModel>(() => reviveModel(store.get(STORAGE_KEY)) ?? initialModel());
  const [toast, setToast] = useState<string | null>(null);
  // Which exam the route, the map and the set list show; starts on the exam of the set in work
  const [exam, setExam] = useState<ExamId>(() => (model.currentSet ? setById(model.currentSet).exam : "sat"));
  // The set opened on «Сеты»: its graph and topics replace the list until the student goes back
  const [openSet, setOpenSet] = useState<{ id: string; topic?: string } | null>(null);
  const [showDiagnostic, setShowDiagnostic] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const isDiagPending = !model.diagnosticDone;

  // Без входного замера доступна исключительно вкладка «Сейчас»
  useEffect(() => {
    if (isDiagPending) {
      if (tab !== "overview") onTab("overview");
      if (sub !== "now") onSub("now");
    }
  }, [isDiagPending, tab, sub, onTab, onSub]);

  // A sub-tab belongs to its tab; switching tabs falls back to the first one
  const current = isDiagPending ? "now" : subFor(tab, sub);

  useEffect(() => {
    onDiagnosticStatusChange?.(Boolean(model.diagnosticDone));
  }, [model.diagnosticDone, onDiagnosticStatusChange]);

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
  // An open set and the map are drawings: they take all the height left
  const setOpen = programs.length > 0 && tab === "sets" && current === "route" && !!openSet;
  const fill = setOpen || (programs.length > 0 && tab === "sets" && current === "map");

  const intro = INTROS[setOpen ? "set" : current];

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
      onSub("route");
      setExam(setById(id).exam);
    });

  const accept = (id: string) => {
    setModel((m) => acceptSet(m, id));
    setToast("Сет принят — начни с первой темы на графе");
    openSetAt(id);
  };

  const choose = (id: string) => {
    setModel((m) => makeCurrent(m, id));
    setToast(`Сет ${setById(id).number} в работе`);
  };

  const skipDiagnostic = () => {
    setModel((m) => ({
      ...m,
      diagnosticDone: true,
      diagnosticSkipped: true,
    }));
    setShowDiagnostic(false);
    onCloseExternalDiagnostic?.();
    onDiagnosticStatusChange?.(true);
    setToast("Входной тест пропущен — применены базовые оценки знаний. Все вкладки открыты.");
  };

  const completeDiagnostic = (summary: DiagnosticResultSummary) => {
    setModel((m) => ({
      ...m,
      diagnosticDone: true,
      diagnosticSkipped: false,
      states: { ...m.states, ...summary.statesUpdate },
    }));
    setShowDiagnostic(false);
    onCloseExternalDiagnostic?.();
    onDiagnosticStatusChange?.(true);
    setToast(`Входной замер завершён: ${summary.score} из 8. Маршрут успешно откалиброван!`);
  };

  const isDiagModalOpen = showDiagnostic || Boolean(externalOpenDiagnostic);

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
            {!saved.length && (
              <FirstHint id="prep-demo" title="Это пример" action={{ label: "Перейти к выбору", onClick: onGoToChoice }}>
                План собран на демо-программах. Сохрани свои в «Выборе», и подготовка пересоберётся под их экзамены и сроки.
              </FirstHint>
            )}
            <FirstHint key={intro.id} id={intro.id} title={intro.title}>
              {intro.text}
            </FirstHint>

            {/* Tabs and their parts are picked only in the left column — on phones it is the menu drawer */}
            <div key={`${tab}-${current}-${openSet?.id ?? ""}`} className={styles.tabBody}>
              {isDiagPending ? (
                /* До прохождения теста доступна исключительно вкладка «Сейчас» */
                <Overview
                  model={model}
                  programs={programs}
                  sub="now"
                  onGo={() => setShowDiagnostic(true)}
                  onOpenSet={() => setShowDiagnostic(true)}
                  onAccept={() => setShowDiagnostic(true)}
                  onOpenDiagnostic={() => setShowDiagnostic(true)}
                  onSkipDiagnostic={skipDiagnostic}
                />
              ) : (
                <>
                  {tab === "overview" && (
                    <Overview
                      model={model}
                      programs={programs}
                      sub={current}
                      onGo={go}
                      onOpenSet={openSetAt}
                      onAccept={accept}
                      onOpenDiagnostic={() => setShowDiagnostic(true)}
                      onSkipDiagnostic={skipDiagnostic}
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
                      onOpenDiagnostic={() => setShowDiagnostic(true)}
                    />
                  )}
                </>
              )}
            </div>
          </>
        )}
      </div>

      {isDiagModalOpen && (
        <DiagnosticMock
          onComplete={completeDiagnostic}
          onClose={() => {
            setShowDiagnostic(false);
            onCloseExternalDiagnostic?.();
          }}
          onSkip={skipDiagnostic}
        />
      )}

      {toast && (
        <div className={styles.toast} role="status">
          {toast}
        </div>
      )}
    </div>
  );
}
