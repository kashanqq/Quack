"use client";

import { Icon } from "../choice/Icon";
import type { Signal } from "../quack/contract";
import styles from "./dashboard.module.css";

type Target = NonNullable<Signal["target"]>;

type Props = {
  fresh: Signal[];
  history: Signal[];
  /** New for this visit: fresh now, or fresh when the student opened Quack */
  isNew: (signal: Signal) => boolean;
  onTarget: (target: Target) => void;
};

const TONE_ICON = { up: "trending-up", down: "trending-down", info: "info" } as const;
const TARGET_LABEL: Record<Target, string> = {
  prep: "Открыть подготовку",
  calendar: "Открыть календарь",
  programs: "Открыть программы",
  profile: "Открыть профиль",
};
const SHOWN = 8;

function ago(iso: string) {
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60_000);
  if (minutes < 1) return "только что";
  if (minutes < 60) return `${minutes} мин назад`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} ч назад`;
  return new Date(iso).toLocaleDateString("ru-RU", { day: "numeric", month: "short" });
}

/** Why the Quack! button glowed: every change since the last visit, then the ones already seen. */
export function ChangesFeed({ fresh, history, isNew, onTarget }: Props) {
  const key = (s: Signal) => `${s.id}@${s.at}`;
  const items = [...fresh, ...history].filter((s, i, all) => all.findIndex((x) => key(x) === key(s)) === i).slice(0, SHOWN);
  const newCount = items.filter(isNew).length;

  return (
    <section className={styles.card} aria-label="Что изменилось">
      <header className={styles.cardHead}>
        <h3>Что изменилось</h3>
        {newCount > 0 && <span className={styles.counter}>{newCount} нов.</span>}
      </header>

      {items.length === 0 ? (
        <p className={styles.muted}>
          Пока тихо. Как только что-то пересчитается — профиль, избранное или подготовка, — это появится здесь, а кнопка Quack!
          засветится.
        </p>
      ) : (
        <ol className={styles.feed}>
          {items.map((s) => (
            <li
              key={key(s)}
              className={styles.feedItem}
              data-level={s.level}
              data-tone={s.tone}
              data-new={isNew(s)}
            >
              <span className={styles.feedIcon}>
                <Icon name={TONE_ICON[s.tone]} size={16} />
              </span>
              <div className={styles.feedBody}>
                <p className={styles.feedTitle}>{s.title}</p>
                {s.detail && <p className={styles.feedDetail}>{s.detail}</p>}
                <p className={styles.feedMeta}>{[s.cause, ago(s.at)].filter(Boolean).join(" · ")}</p>
              </div>
              {s.target && s.target !== "profile" && (
                <button
                  type="button"
                  className={styles.feedGo}
                  aria-label={TARGET_LABEL[s.target]}
                  title={TARGET_LABEL[s.target]}
                  onClick={() => onTarget(s.target!)}
                >
                  <Icon name="chevron-right" size={16} />
                </button>
              )}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
