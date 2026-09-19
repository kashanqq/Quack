"use client";

import { useState } from "react";
import type { Profile } from "../choice/assistant";
import { Icon } from "../choice/Icon";
import { LevelBadge } from "../choice/ProgramUi";
import { evaluate, formatEur } from "../choice/programs";
import type { RemovalEffect, Watch } from "./dashboardRules";
import styles from "./dashboard.module.css";

type Props = {
  effects: RemovalEffect[];
  watch: Watch[];
  profile: Profile;
  /** Forecast score from «Подготовки», the section's answer back to the saved programs */
  predicted: number;
  watched: string[];
  onWatch: (id: string) => void;
  onUnsave: (id: string) => void;
};

/** Saved programs: what depends on each of them and what stopped fitting the profile. */
export function ProgramsTab({ effects, watch, profile, predicted, watched, onWatch, onUnsave }: Props) {
  const [open, setOpen] = useState<string | null>(null);

  return (
    <>
      <section className={styles.card} aria-label="Связь в обе стороны">
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
                <button type="button" className={styles.effectHead} onClick={() => setOpen((id) => (id === e.program.id ? null : e.program.id))}>
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

                {open === e.program.id && (
                  <div className={styles.effectBody}>
                    {e.drops.length > 0 && (
                      <p>
                        Если убрать: {e.drops.join(", ")} больше никому не нужен и уйдёт из подготовки и календаря.{" "}
                        <span className={styles.muted}>
                          Всё, что ты уже выучил, останется — вернёшь программу, ничего заново проходить не нужно.
                        </span>
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

      <section className={styles.card} aria-label="Под присмотром">
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
                    <Icon name="star" size={14} /> оставлена, следим за оценкой
                  </span>
                ) : (
                  <div className={styles.actions}>
                    <button type="button" className={styles.secondary} onClick={() => onWatch(w.program.id)}>
                      Оставить
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
    </>
  );
}
