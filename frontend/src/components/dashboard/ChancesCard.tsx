"use client";

import { Icon } from "../choice/Icon";
import type { AdviceAction, PaceLevel, Signal, Standing } from "../quack/contract";
import styles from "./dashboard.module.css";

type Props = {
  standing: Standing;
  /** Fresh signals, to mark the programs whose chances just moved */
  fresh: Signal[];
  onOpenPrep: () => void;
  onOpenCalendar: () => void;
  onOpenPrograms: () => void;
  /** Ticks a milestone done: the registration a verdict waits for */
  onMark: (milestone: string) => void;
  decisions: Decisions;
};

/** What the student does with a piece of advice: take it, or put it aside until its reason changes */
type Decisions = {
  dismissed: string[];
  onAct: (action: AdviceAction) => void;
  onDismiss: (advice: string, hide: boolean) => void;
};

/**
 * Advice with its two answers (product-logic §3.6): «Сделать» changes the plan as the student would, «Не сейчас»
 * hides it until its words — and so its reason — change. Hidden advice can be brought back.
 */
function AdviceList({
  advice,
  actions,
  decisions,
  compact,
}: {
  advice: string[];
  actions?: (AdviceAction | null)[];
  decisions: Decisions;
  compact?: boolean;
}) {
  const shown = advice.map((text, i) => ({ text, action: actions?.[i] ?? null })).filter((a) => !decisions.dismissed.includes(a.text));
  const hidden = advice.filter((text) => decisions.dismissed.includes(text));
  return (
    <>
      <ul className={compact ? styles.adviceCompact : undefined}>
        {shown.map(({ text, action }) => (
          <li key={text}>
            <span>{text}</span>
            <span className={styles.adviceActions}>
              {action && (
                <button type="button" className={styles.markButton} onClick={() => decisions.onAct(action)}>
                  {action.label}
                </button>
              )}
              <button type="button" className={styles.adviceLater} onClick={() => decisions.onDismiss(text, true)}>
                Не сейчас
              </button>
            </span>
          </li>
        ))}
      </ul>
      {hidden.length > 0 && (
        <button type="button" className={styles.inlineLink} onClick={() => hidden.forEach((text) => decisions.onDismiss(text, false))}>
          Отложено советов: {hidden.length} · показать
        </button>
      )}
    </>
  );
}

const examWord = (n: number) =>
  n % 10 === 1 && n % 100 !== 11 ? "экзамен" : n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 10 || n % 100 >= 20) ? "экзамена" : "экзаменов";

function PaceMeter({ level, label }: { level: PaceLevel; label: string }) {
  return (
    <span className={styles.paceMeter} role="img" aria-label={`Темп: ${label}`}>
      {([0, 1, 2, 3] as const).map((step) => (
        <span key={step} data-on={step <= level} />
      ))}
    </span>
  );
}

/** The tick right where the verdict says what it waits for */
function MarkButton({ mark, onMark }: { mark: { milestone: string; label: string }; onMark: (milestone: string) => void }) {
  return (
    <button type="button" className={`${styles.markButton} ${styles.markInline}`} onClick={() => onMark(mark.milestone)}>
      <Icon name="check" size={14} /> {mark.label}
    </button>
  );
}

/**
 * The top of Quack (product-logic §3.6): will the student be ready by the tests — on track, needs to
 * speed up (and how), or can no longer make it (and what is left) — and where the saved programs stand.
 */
export function ChancesCard({ standing, fresh, onOpenPrep, onOpenCalendar, onOpenPrograms, onMark, decisions }: Props) {
  const { pace, exams, programs, next } = standing;
  const others = exams.filter((e) => e.id !== pace?.exam);
  const trend = (id: string) => fresh.find((s) => s.kind === "chance" && s.subject === id)?.tone;

  return (
    <section className={`${styles.card} ${styles.wide}`} aria-label="Шансы">
      <header className={styles.cardHead}>
        <h3>Шансы</h3>
        <span className={styles.muted}>успеешь ли к тестам и что с программами</span>
      </header>

      {pace && (
        <div className={styles.verdict} data-pace={pace.level}>
          <div className={styles.verdictHead}>
            <strong className={styles.verdictLabel}>{pace.verdict}</strong>
            <PaceMeter level={pace.level} label={pace.verdict} />
          </div>
          <p className={styles.verdictSummary}>{pace.summary}</p>
          {pace.advice.length > 0 && (
            <div className={styles.advice}>
              <p className={styles.adviceTitle}>{pace.level === 0 ? "Что можно сделать" : "Как ускориться"}</p>
              <AdviceList advice={pace.advice} actions={pace.adviceActions} decisions={decisions} />
              {pace.mark && <MarkButton mark={pace.mark} onMark={onMark} />}
            </div>
          )}
        </div>
      )}

      {others.length > 0 && (
        <ul className={styles.examPaces}>
          {others.map((e) => (
            <li key={e.id} data-pace={e.level}>
              <span className={styles.examPaceHead}>
                <b>{e.name}</b>
                <span className={styles.examPaceVerdict}>{e.verdict}</span>
              </span>
              <span className={styles.muted}>{e.summary}</span>
              {e.advice.length > 0 && <AdviceList advice={e.advice} actions={e.adviceActions} decisions={decisions} compact />}
              {e.mark && <MarkButton mark={e.mark} onMark={onMark} />}
            </li>
          ))}
        </ul>
      )}

      <p className={styles.chanceTitle}>Программы</p>
      <ul className={styles.chanceList}>
        {programs.map((p) => {
          const tone = trend(p.id);
          return (
            <li key={p.id}>
              <button
                type="button"
                className={styles.chanceItem}
                data-level={p.level}
                title={p.facts.map((f) => `${f.label}: ${f.have}, нужно ${f.need}`).join("\n")}
                onClick={onOpenPrograms}
              >
                <span className={styles.chanceDot} aria-hidden="true" />
                <span className={styles.chanceName}>{p.university}</span>
                <span className={styles.chanceLevel}>{p.levelLabel}</span>
                {tone && tone !== "info" && (
                  <span className={styles.chanceTrend} data-tone={tone} aria-label={tone === "up" ? "шансы выросли" : "шансы снизились"}>
                    <Icon name={tone === "up" ? "trending-up" : "trending-down"} size={14} />
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ul>

      <footer className={styles.chancesFoot}>
        <span className={styles.muted}>
          {exams.length} {examWord(exams.length)}
          {next && (
            <>
              {" · "}
              <button type="button" className={styles.inlineLink} onClick={onOpenCalendar}>
                ближайшая дата через {next.daysLeft} дн.: {next.title.toLowerCase()}
              </button>
            </>
          )}
        </span>
        <button type="button" className={styles.secondary} onClick={onOpenPrep}>
          <Icon name="book-open-check" size={16} /> Открыть подготовку
        </button>
      </footer>
    </section>
  );
}
