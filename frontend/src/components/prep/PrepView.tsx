"use client";

// "Подготовка" (product-logic §4). Input of the section is the saved programs; with none saved the
// student can look at it on demo programs. Its state lives in localStorage until there is a backend.

import { useEffect, useRef, useState } from "react";
import { Icon } from "../choice/Icon";
import { CurrentSet } from "./CurrentSet";
import { Overview } from "./Overview";
import { savedPrograms } from "./prepData";
import { acceptSet, initialModel, makeCurrent, PREP_TABS, reviveModel, type PrepModel, type PrepTab } from "./prepModel";
import { SetsView } from "./SetsView";
import styles from "./prep.module.css";

const STORAGE_KEY = "quack-prep";

type Props = {
  tab: PrepTab;
  onTab: (tab: PrepTab) => void;
  saved: string[];
  onGoToChoice: () => void;
};

export function PrepView({ tab, onTab, saved, onGoToChoice }: Props) {
  // Rendered only after the student switches to the section, so storage can be read right away
  const [model, setModel] = useState<PrepModel>(() => {
    try {
      return reviveModel(JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null")) ?? initialModel();
    } catch {
      return initialModel();
    }
  });
  const [toast, setToast] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(model));
    } catch {}
  }, [model]);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 3200);
    return () => clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: 0 });
  }, [tab]);

  const programs = savedPrograms(saved, model.demo);

  const accept = (id: string) => {
    setModel((m) => acceptSet(m, id));
    setToast("Сет принят — он в «Текущем сете»");
    onTab("current");
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
              ? `По ${saved.length ? "сохранённым" : "демо-"}программам: ${programs.map((p) => p.university).join(", ")}`
              : "Вход раздела — сохранённые программы"}
          </p>
        </div>
        {programs.length > 0 && (
          <div className={styles.tabs} role="tablist" aria-label="Разделы подготовки">
            {PREP_TABS.map((t) => (
              <button key={t.tab} type="button" role="tab" aria-selected={tab === t.tab} onClick={() => onTab(t.tab)}>
                <Icon name={t.icon} size={16} />
                {t.label}
              </button>
            ))}
          </div>
        )}
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
          <div key={tab} className={styles.tabBody}>
            {tab === "overview" && (
              <Overview
                model={model}
                programs={programs}
                onTab={onTab}
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
            {tab === "sets" && <SetsView model={model} onMakeCurrent={choose} onModel={setModel} />}
            {tab === "current" && <CurrentSet model={model} onModel={setModel} onAccept={accept} onTab={onTab} onToast={setToast} />}
          </div>
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
