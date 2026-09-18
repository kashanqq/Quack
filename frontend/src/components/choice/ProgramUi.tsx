"use client";

import { useEffect, useRef } from "react";
import type { Profile } from "./assistant";
import { Icon } from "./Icon";
import { LEVEL_LABEL, evaluate, formatEur, programById, type Level } from "./programs";
import styles from "./layout.module.css";

export type ProgramActions = {
  saved: string[];
  compare: string[];
  onToggleSave: (id: string) => void;
  onToggleCompare: (id: string) => void;
  onOpen: (id: string) => void;
};

export function LevelBadge({ level }: { level: Level }) {
  return <span className={`${styles.level} ${styles[level]}`}>{LEVEL_LABEL[level]}</span>;
}

export function LevelDot({ level }: { level: Level }) {
  return <span className={`${styles.levelDot} ${styles[level]}`} title={LEVEL_LABEL[level]} />;
}

/** Horizontal row of program cards posted by the assistant into the chat. */
/**
 * A mouse wheel only goes up and down, so over the cards it turns them sideways instead. Once the row
 * reaches its first or last card the wheel is let through, and the chat scrolls on as usual.
 */
function useSidewaysWheel() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const row = ref.current;
    if (!row) return;
    const onWheel = (e: WheelEvent) => {
      // A trackpad already swipes sideways, and Ctrl + wheel is the browser's zoom
      if (e.ctrlKey || Math.abs(e.deltaX) >= Math.abs(e.deltaY)) return;
      const max = row.scrollWidth - row.clientWidth;
      if (max <= 0) return;
      const atEnd = e.deltaY > 0 ? row.scrollLeft >= max - 1 : row.scrollLeft <= 0;
      if (atEnd) return;
      e.preventDefault();
      // Lines (Firefox) and pages come in other units than pixels
      const step = e.deltaMode === 1 ? 40 : e.deltaMode === 2 ? row.clientWidth : 1;
      row.scrollBy({ left: e.deltaY * step });
    };
    row.addEventListener("wheel", onWheel, { passive: false });
    return () => row.removeEventListener("wheel", onWheel);
  }, []);

  return ref;
}

export function ProgramCards({ ids, profile, actions }: { ids: string[]; profile: Profile; actions: ProgramActions }) {
  const rowRef = useSidewaysWheel();

  return (
    <div className={styles.cards} ref={rowRef}>
      {ids.map((id, i) => {
        const program = programById(id);
        const evaluation = evaluate(program, profile);
        const saved = actions.saved.includes(id);
        const comparing = actions.compare.includes(id);

        return (
          <article key={id} className={styles.card} style={{ animationDelay: `${i * 90}ms` }}>
            <div className={styles.cardTop}>
              <LevelBadge level={evaluation.level} />
              <span className={styles.demo}>демо</span>
            </div>
            <h3 className={styles.cardUni}>{program.university}</h3>
            <p className={styles.cardProgram}>{program.program}</p>
            <p className={styles.cardMeta}>
              {program.city}, {program.country} · {formatEur(program.costEur)}
            </p>
            <p className={styles.cardFit}>
              {evaluation.fits.length > 0 && (
                <>
                  <span className={styles.fitLabel}>Подходит тебе:</span> {evaluation.fits.join(", ")}
                </>
              )}
              {evaluation.misfits.length > 0 && (
                <>
                  {evaluation.fits.length > 0 && <br />}
                  <span className={styles.fitLabel}>Но:</span> {evaluation.misfits.join(", ")}
                </>
              )}
            </p>
            <div className={styles.cardActions}>
              <button
                type="button"
                className={`${styles.pillButton} ${styles.saveButton}`}
                aria-pressed={saved}
                aria-label={saved ? "Убрать из избранного" : "В избранное"}
                onClick={() => actions.onToggleSave(id)}
              >
                <Icon name="star" size={16} />
              </button>
              <button
                type="button"
                className={styles.pillButton}
                aria-pressed={comparing}
                onClick={() => actions.onToggleCompare(id)}
              >
                <Icon name="git-compare" size={16} />
                {comparing ? "В сравнении" : "Сравнить"}
              </button>
              <button type="button" className={`${styles.pillButton} ${styles.cardMore}`} onClick={() => actions.onOpen(id)}>
                Подробнее
              </button>
            </div>
          </article>
        );
      })}
    </div>
  );
}

/** Slide-in panel with every factor behind the realism level. */
export function ProgramDrawer({
  id,
  profile,
  actions,
  onClose,
}: {
  id: string | null;
  profile: Profile;
  actions: ProgramActions;
  onClose: () => void;
}) {
  const program = id ? programById(id) : null;
  const evaluation = program ? evaluate(program, profile) : null;

  return (
    <div className={`${styles.drawerLayer} ${program ? styles.drawerOpen : ""}`} aria-hidden={!program}>
      <div className={styles.backdrop} onClick={onClose} />
      <aside className={styles.drawer} role="dialog" aria-label={program?.university}>
        {program && evaluation && (
          <>
            <div className={styles.drawerHead}>
              <LevelBadge level={evaluation.level} />
              <button type="button" className={styles.iconButton} aria-label="Закрыть" onClick={onClose}>
                <Icon name="x" />
              </button>
            </div>
            <div className={styles.drawerBody} key={program.id}>
              <h2 className={styles.drawerUni}>{program.university}</h2>
              <p className={styles.drawerProgram}>{program.program}</p>
              <p className={styles.drawerMeta}>
                {program.city}, {program.country} · {program.duration} · подача до {program.deadline} ·{" "}
                <span className={styles.demo}>демо-данные</span>
              </p>

              <h3 className={styles.sectionTitle}>Реалистичность — из чего складывается</h3>
              <ul className={styles.factors}>
                {evaluation.factors.map((f, i) => (
                  <li key={f.label} className={styles.factor} style={{ animationDelay: `${i * 60}ms` }}>
                    <span
                      className={`${styles.factorMark} ${
                        f.status === "ok" ? styles.factorOk : f.status === "below" ? styles.factorBelow : styles.factorUnknown
                      }`}
                    />
                    <span className={styles.factorLabel}>
                      {f.label}: {f.value}
                    </span>
                    <span className={styles.factorNote}>{f.note}</span>
                  </li>
                ))}
              </ul>

              <h3 className={styles.sectionTitle}>Подходит тебе</h3>
              {evaluation.fits.length || evaluation.misfits.length ? (
                <ul className={styles.fitList}>
                  {evaluation.fits.map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                  {evaluation.misfits.map((f) => (
                    <li key={f}>но: {f}</li>
                  ))}
                </ul>
              ) : (
                <p className={styles.factorNote}>Расскажи в чате, что тебе важно, — и я объясню, чем программа подходит.</p>
              )}

              <h3 className={styles.sectionTitle}>Среда</h3>
              <p className={styles.factorNote}>
                Наука: {program.research}. Обмен: {program.exchange}. Язык: {program.language}.
              </p>
            </div>
            <div className={styles.drawerActions}>
              <button
                type="button"
                className={`${styles.pillButton} ${styles.saveButton}`}
                aria-pressed={actions.saved.includes(program.id)}
                onClick={() => actions.onToggleSave(program.id)}
              >
                <Icon name="star" size={16} />
                {actions.saved.includes(program.id) ? "В избранном" : "В избранное"}
              </button>
              <button
                type="button"
                className={styles.pillButton}
                aria-pressed={actions.compare.includes(program.id)}
                onClick={() => actions.onToggleCompare(program.id)}
              >
                <Icon name="git-compare" size={16} />
                {actions.compare.includes(program.id) ? "В сравнении" : "Сравнить"}
              </button>
            </div>
          </>
        )}
      </aside>
    </div>
  );
}
