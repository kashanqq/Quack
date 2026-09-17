"use client";

import { useEffect, useRef, useState } from "react";
import { usePageTransition } from "@/components/transition/TransitionProvider";
import { TransitionLink } from "@/components/transition/TransitionLink";
import { Icon } from "./Icon";
import styles from "./choice.module.css";
import layout from "./layout.module.css";

type TopbarProps = {
  onRestart: () => void;
  /** Toggle for the "Как я тебя вижу" panel; omitted while it isn't available */
  profilePanel?: { open: boolean; onToggle: () => void };
  /** Opens the left column (programs, chats) on phones */
  onOpenPrograms: () => void;
};

export function Topbar({ onRestart, profilePanel, onOpenPrograms }: TopbarProps) {
  const { runWithLoader } = usePageTransition();
  const [open, setOpen] = useState(false);
  const userRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (!userRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("click", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("click", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <header className={styles.topbar}>
      <TransitionLink className={styles.topbarLogo} href="/">
        Quack<span className={styles.accent}>!</span>
      </TransitionLink>

      <div className={styles.user} ref={userRef}>
        <button
          className={styles.userButton}
          type="button"
          aria-haspopup="menu"
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          <img className={styles.userAvatar} src="/assets/avatar.svg" alt="" />
          <span className={styles.userName}>user_name</span>
          <img className={styles.userChevron} src="/assets/chevron-down.svg" alt="" />
        </button>
        <div className={`${styles.userMenu} ${open ? styles.isOpen : ""}`} role="menu">
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setOpen(false);
              runWithLoader(onRestart);
            }}
          >
            Начать заново
          </button>
          <TransitionLink role="menuitem" href="/">
            Выйти
          </TransitionLink>
        </div>
      </div>

      <div className={styles.topbarActions}>
        <button
          type="button"
          className={`${layout.iconButton} ${styles.mobileOnly}`}
          aria-label="Меню: программы и чаты"
          onClick={onOpenPrograms}
        >
          <Icon name="graduation-cap" />
        </button>
        {profilePanel && (
          <button
            type="button"
            className={layout.iconButton}
            aria-label={profilePanel.open ? "Скрыть «Как я тебя вижу»" : "Показать «Как я тебя вижу»"}
            title="Как я тебя вижу"
            aria-pressed={profilePanel.open}
            onClick={profilePanel.onToggle}
          >
            <Icon name={profilePanel.open ? "panel-right-close" : "panel-right-open"} />
          </button>
        )}
      </div>
    </header>
  );
}
