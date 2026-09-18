"use client";

import { useEffect, useState, type ReactNode } from "react";
import { PixelDuck } from "@/components/duck/PixelDuck";
import styles from "./hints.module.css";

const KEY = "quack-hints-seen";

function readSeen(): string[] {
  try {
    const list = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

/** Forget every dismissed hint, so a fresh start explains the sections again. */
export function resetHints() {
  try {
    localStorage.removeItem(KEY);
  } catch {}
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
  // Hidden until mounted: the server does not know what this browser has already seen
  const [show, setShow] = useState(false);

  useEffect(() => setShow(!readSeen().includes(id)), [id]);

  if (!show) return null;

  const dismiss = () => {
    setShow(false);
    try {
      localStorage.setItem(KEY, JSON.stringify([...new Set([...readSeen(), id])]));
    } catch {}
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
