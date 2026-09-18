"use client";

import { createContext, useContext, useEffect, useId, useRef, useState, type ReactNode } from "react";
import { PixelDuck } from "@/components/duck/PixelDuck";
import styles from "./hints.module.css";
import { store } from "@/components/account/store";

/** How many times each explanation was opened; the second time is the last */
const KEY = "quack-hints-opened";
const LAST_OPEN = 2;

type Opened = Record<string, number>;

function readOpened(): Opened {
  const saved = store.get<Opened>(KEY);
  const opened: Opened = saved && typeof saved === "object" && !Array.isArray(saved) ? { ...saved } : {};
  // Hints read before the duck moved to the column count as opened once
  const seen = store.get<string[]>("quack-hints-seen");
  if (Array.isArray(seen)) for (const id of seen) opened[id] = Math.max(opened[id] ?? 0, 1);
  return opened;
}

type Entry = { key: string; id: string; title: string; body: ReactNode; action?: { label: string; onClick: () => void } };

type Registry = { add: (entry: Entry) => void; remove: (key: string) => void };

type Help = {
  /** What the screen on display explains, most specific first; explanations opened twice are gone */
  shown: Entry[];
  fresh: boolean;
  /** What the open window holds: fixed when it opens, so counting the opening does not empty it */
  open: Entry[] | null;
  openHelp: () => void;
  closeHelp: () => void;
};

const HelpContext = createContext<Registry | null>(null);
const HelpState = createContext<Help | null>(null);

/**
 * Holds what the screens on display explain about themselves. Screens say it with <FirstHint>; a duck
 * with a question mark beside the active item of the left column opens the explanation.
 */
export function HelpProvider({ children }: { children: ReactNode }) {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [opened, setOpened] = useState<Opened>({});
  const [open, setOpen] = useState<Entry[] | null>(null);
  const registry = useRef<Registry>({
    // Updating keeps the place, so a screen that re-renders does not jump ahead of a more specific one
    add: (entry) =>
      setEntries((list) => (list.some((e) => e.key === entry.key) ? list.map((e) => (e.key === entry.key ? entry : e)) : [...list, entry])),
    remove: (key) => setEntries((list) => list.filter((e) => e.key !== key)),
  });

  useEffect(() => setOpened(readOpened()), []);

  // The most specific screen registers last: it goes first
  const shown = [...entries].reverse().filter((e) => (opened[e.id] ?? 0) < LAST_OPEN);

  const help: Help = {
    shown,
    fresh: shown.some((e) => !opened[e.id]),
    open,
    openHelp: () => {
      if (!shown.length) return;
      setOpen(shown);
      const next = readOpened();
      for (const e of shown) next[e.id] = (next[e.id] ?? 0) + 1;
      store.set(KEY, next);
      setOpened(next);
    },
    closeHelp: () => setOpen(null),
  };

  return (
    <HelpContext.Provider value={registry.current}>
      <HelpState.Provider value={help}>{children}</HelpState.Provider>
    </HelpContext.Provider>
  );
}

type Props = {
  /** One id per place, so the duck knows how many times the student has opened it */
  id: string;
  title: string;
  children: ReactNode;
  action?: { label: string; onClick: () => void };
};

/**
 * What this screen is for, in a couple of sentences. Draws nothing where it stands: the text goes to the
 * duck in the left column, so the screen itself stays clear.
 */
export function FirstHint({ id, title, children, action }: Props) {
  const registry = useContext(HelpContext);
  const key = useId();
  useEffect(() => {
    registry?.add({ key, id, title, body: children, action });
  }, [registry, key, id, title, children, action]);
  useEffect(() => () => registry?.remove(key), [registry, key]);
  return null;
}

/** The duck with a question mark; stands at the right end of the active item of the left column. */
export function HelpDuck({ className = "" }: { className?: string }) {
  const help = useContext(HelpState);
  if (!help?.shown.length) return null;
  return (
    <button
      type="button"
      className={`${styles.duck} ${className}`}
      data-fresh={help.fresh || undefined}
      aria-label={`Подсказка: ${help.shown[0].title}`}
      title="Что здесь?"
      onClick={help.openHelp}
    >
      <span className={styles.bubble}>?</span>
      <span className={styles.duckBody}>
        <PixelDuck tempo="chill" />
      </span>
    </button>
  );
}

/** The explanation the duck opens, over the work area */
export function HelpDialog() {
  const help = useContext(HelpState);
  const open = help?.open;
  const close = help?.closeHelp;

  useEffect(() => {
    if (!open || !close) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && close();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, close]);

  if (!open || !close) return null;

  return (
    <div className={styles.backdrop} onClick={close}>
      <div className={styles.dialog} role="dialog" aria-modal="true" aria-label={open[0].title} onClick={(e) => e.stopPropagation()}>
        <PixelDuck tempo="steady" className={styles.dialogDuck} />
        <div className={styles.dialogBody}>
          {open.map((e) => (
            <section key={e.key}>
              <strong>{e.title}</strong>
              <p>{e.body}</p>
              {e.action && (
                <button
                  type="button"
                  className={styles.action}
                  onClick={() => {
                    close();
                    e.action!.onClick();
                  }}
                >
                  {e.action.label}
                </button>
              )}
            </section>
          ))}
          <div className={styles.actions}>
            <button type="button" className={styles.dismiss} onClick={close} autoFocus>
              Понятно
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
