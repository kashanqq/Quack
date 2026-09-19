"use client";

import { examLabel, type UnionExam } from "./dashboardRules";
import styles from "./dashboard.module.css";

/** «Что сдавать»: requirements of every saved program merged into one list. */
export function ExamsTab({
  exams,
  programCount,
  targets,
}: {
  exams: UnionExam[];
  programCount: number;
  /** Targets the student set by hand in «Требованиях»: shown next to the programs' bar */
  targets: Partial<Record<"sat" | "ent", number>>;
}) {
  return (
    <section className={styles.card} aria-label="Что тебе сдавать">
      <header className={styles.cardHead}>
        <h3>Что тебе сдавать</h3>
        <span className={styles.muted}>требования {programCount} программ сведены в один список</span>
      </header>

      <div className={styles.exams}>
        {exams.map((union) => (
          <article key={union.exam.id} className={styles.exam}>
            <div className={styles.examTop}>
              <strong>{examLabel(union)}</strong>
              {union.exam.id !== "ielts" && targets[union.exam.id] !== undefined && (
                <span className={styles.muted}>твоя цель — {targets[union.exam.id]}</span>
              )}
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
  );
}
