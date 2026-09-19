"use client";

// "Подготовка" (product-logic §4). Input of the section is the saved programs; with none saved the
// student can look at it on demo programs. Its state is kept in the student's store (account/store.ts).

import { FirstHint } from "@/components/hints/FirstHint";
import { useEffect, useRef, useState } from "react";
import { morph } from "@/components/transition/morph";
import { Overview } from "./Overview";
import { prefetchRemoteOverview } from "./remotePrep";
import {
  openRemoteSet,
  prefetchRemoteSets,
  REMOTE_PREP,
  switchRemoteSet,
} from "./remoteSets";
import { savedPrograms, setById, type ExamId } from "./prepData";
import {
  acceptSet,
  initialModel,
  makeCurrent,
  rankSets,
  reviveModel,
  subFor,
  type PrepModel,
  type PrepSub,
  type PrepTab,
} from "./prepModel";
import { quackSource } from "../quack/source";
import { SetsView } from "./SetsView";
import type { DiagnosticResultSummary } from "./diagnosticData";
import styles from "./prep.module.css";
import { store } from "../account/store";

const STORAGE_KEY = "quack-prep";

/** One first-visit note per part of the section: what it shows and what to press. The ids are kept once seen. */
const INTROS: Record<PrepSub, { id: string; title: string; text: string }> = {
  now: {
    id: "prep-now-v2",
    title: "Зачем «Подготовка»",
    text: "Здесь план подготовки к экзаменам, которые требуют твои программы. «Сейчас» — твоё место для занятий: активный сет и его темы на шкале до дедлайна. Нажми на тему — откроется чат с ассистентом и мок-тест рядом.",
  },
  requirements: {
    id: "prep-requirements",
    title: "Что такое «Требования»",
    text: "Какие экзамены и на какой балл нужны сохранённым программам, и когда ты, по прогнозу, будешь готов. Цели пересчитываются, когда меняется список программ.",
  },
  route: {
    id: "prep-route-v3",
    title: "Что такое маршрут",
    text: "Сет — несколько связанных тем с общим дедлайном. Сверху — сет, над которым ты работаешь, ниже — советы ассистента по твоим ошибкам. Не нравится текущий — сделай актуальным другой, а текущий уйдёт в отложенные, прогресс по темам не теряется.",
  },
  map: {
    id: "prep-map-v2",
    title: "Как читать карту навыков",
    text: "Слева направо: последние пройденные сеты, сет в работе и не больше трёх советов ассистента. На каждой карточке — её темы и как они держатся. Нажми на тему, чтобы открыть её; «⋯» слева показывает всю историю.",
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
  // A topic of the active set asked for from elsewhere (a trap, the map): «Сейчас» opens it
  const [focus, setFocus] = useState<{ topic?: string; n: number } | null>(null);
  // Another set asked for from elsewhere: «Маршрут» shows its card open
  const [routeFocus, setRouteFocus] = useState<string | null>(null);
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
  }, [tab, current, focus?.n]);

  const programs = savedPrograms(saved, model.demo);

  useEffect(() => {
    prefetchRemoteOverview(programs);
  }, [programs.length]);

  useEffect(() => {
    if (REMOTE_PREP) {
      prefetchRemoteSets(exam);
    }
  }, [exam]);

  // Asked to open the test from outside (a locked tab in the column): it runs in «Сейчас»
  const diagOpen = showDiagnostic || Boolean(externalOpenDiagnostic);
  const closeDiagnostic = () => {
    setShowDiagnostic(false);
    onCloseExternalDiagnostic?.();
  };
  // The active set in «Сейчас» and the map are drawings: they take all the height left
  const working = tab === "overview" && current === "now" && !isDiagPending && !diagOpen && !!model.currentSet;
  const fill = programs.length > 0 && (working || (tab === "sets" && current === "map"));

  const intro = INTROS[current];

  /** One move for both levels, so a jump across the section is a single animated step */
  const go = (next: PrepTab, nextSub?: PrepSub, nextExam?: ExamId) =>
    morph(() => {
      onTab(next);
      if (nextSub) onSub(nextSub);
      if (nextExam) setExam(nextExam);
    });

  /**
   * A set asked for from anywhere in the section: the active one is worked on in «Сейчас»,
   * any other is shown in «Маршрут», where it can be made the active one.
   */
  const openSetAt = (id: string, topic?: string) =>
    morph(() => {
      if (id === model.currentSet) {
        setFocus({ topic, n: Date.now() });
        onTab("overview");
        onSub("now");
        return;
      }
      setRouteFocus(id);
      setExam(setById(id).exam);
      onTab("sets");
      onSub("route");
    });

  /** Takes the proposed set into work: it opens right there in «Сейчас» */
  const accept = (id: string) => {
    setModel((m) => acceptSet(m, id));
    setFocus(null);
    setToast("Сет принят — начни с первой темы на графе");
    if (REMOTE_PREP) {
      openRemoteSet(id, exam).catch((err) => {
        console.error("Failed to open remote set:", err);
      });
    }
    go("overview", "now");
  };

  /** From «Маршрут»: the set becomes the active one, the previous one is put aside; the student stays */
  const choose = (id: string) => {
    const prev = model.currentSet;
    setModel((m) => makeCurrent(m, id));
    setFocus(null);
    setRouteFocus(null);
    setToast(
      prev && prev !== id
        ? `Сет ${setById(id).number} теперь актуальный, сет ${setById(prev).number} отложен · занятия — во вкладке «Сейчас»`
        : `Сет ${setById(id).number} теперь актуальный · занятия — во вкладке «Сейчас»`
    );
    if (REMOTE_PREP) {
      switchRemoteSet(id, exam).catch((err) => {
        console.error("Failed to switch remote set:", err);
      });
    }
  };

  const skipDiagnostic = () => {
    setModel((m) => ({ ...m, diagnosticDone: true, diagnosticSkipped: true }));
    closeDiagnostic();
    onDiagnosticStatusChange?.(true);
    setToast("Входной тест пропущен — применены базовые оценки знаний. Все вкладки открыты.");
  };

  const completeDiagnostic = (summary: DiagnosticResultSummary) => {
    setModel((m) => {
      const next = { ...m, diagnosticDone: true, diagnosticSkipped: false, states: { ...m.states, ...summary.statesUpdate } };
      // The first test builds the route: its top set becomes the first one in work. A retake leaves the choice alone.
      if (m.diagnosticDone && m.currentSet) return next;
      const top = rankSets(next, "sat")[0]?.set;
      return top ? acceptSet(next, top.id) : next;
    });
    closeDiagnostic();
    setFocus(null);
    onDiagnosticStatusChange?.(true);
    setToast(`Входной замер завершён: ${summary.score} из 8. Маршрут собран — начни с первой темы на графе`);
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
            {!saved.length && (
              <FirstHint id="prep-demo" title="Это пример" action={{ label: "Перейти к выбору", onClick: onGoToChoice }}>
                План собран на демо-программах. Сохрани свои в «Выборе», и подготовка пересоберётся под их экзамены и сроки.
              </FirstHint>
            )}
            {!diagOpen && (
              <FirstHint key={intro.id} id={intro.id} title={intro.title}>
                {intro.text}
              </FirstHint>
            )}

            {/* Tabs and their parts are picked only in the left column — on phones it is the menu drawer */}
            <div key={`${tab}-${current}`} className={styles.tabBody}>
              {tab === "overview" || isDiagPending ? (
                <Overview
                  model={model}
                  programs={programs}
                  sub={current}
                  onGo={go}
                  onOpenSet={openSetAt}
                  onAccept={accept}
                  onModel={setModel}
                  onToast={setToast}
                  focus={focus}
                  diagnostic={{
                    open: diagOpen,
                    onStart: () => setShowDiagnostic(true),
                    // The first test can only be finished or skipped; a retake can be left
                    onClose: isDiagPending ? undefined : closeDiagnostic,
                    onComplete: completeDiagnostic,
                    onSkip: skipDiagnostic,
                  }}
                />
              ) : (
                <SetsView
                  model={model}
                  sub={current}
                  exam={exam}
                  onExam={setExam}
                  onMakeCurrent={choose}
                  focus={routeFocus}
                  onOpenSet={openSetAt}
                  onGoNow={() => go("overview", "now")}
                  onOpenDiagnostic={() => {
                    setShowDiagnostic(true);
                    go("overview", "now");
                  }}
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
