"use client";

import { useEffect, useState, type ReactNode } from "react";
import { PixelDuck } from "@/components/duck/PixelDuck";
import styles from "./hints.module.css";
import { store } from "@/components/account/store";

const KEY = "quack-hints-seen";

function readSeen(): string[] {
  const list = store.get<string[]>(KEY);
  return Array.isArray(list) ? list : [];
}

type Props = {
  /** One id per place: a hint is shown until the student dismisses it, then never again */
  id: string;
  title: string;
  children: ReactNode;
  action?: { label: string; onClick: () => void };
};

/**
 * One short note the first time a student reaches a section: what it is for and where to start.
 * No tour, no steps, no arrows over buttons — a single card that goes away for good.
 */
export function FirstHint({ id, title, children, action }: Props) {
  // Hidden until mounted: the server render does not know what this student has already seen
  const [show, setShow] = useState(false);

  useEffect(() => setShow(!readSeen().includes(id)), [id]);

  if (!show) return null;

  const dismiss = () => {
    setShow(false);
    store.set(KEY, [...new Set([...readSeen(), id])]);
  };

  return (
    <aside className={styles.hint} aria-label={title}>
      <PixelDuck tempo="chill" className={styles.duck} />
      <div className={styles.body}>
        <strong>{title}</strong>
        <p>{children}</p>
        <div className={styles.actions}>
          {action && (
            <button
              type="button"
              className={styles.action}
              onClick={() => {
                dismiss();
                action.onClick();
              }}
            >
              {action.label}
            </button>
          )}
          <button type="button" className={styles.dismiss} onClick={dismiss}>
            Понятно
          </button>
        </div>
      </div>
    </aside>
  );
}
