"use client";

import { useEffect, useRef, useState } from "react";
import { usePageTransition } from "@/components/transition/TransitionProvider";
import { TransitionLink } from "@/components/transition/TransitionLink";
import styles from "./choice.module.css";

/** Avatar with the account menu, at the bottom of the left column. The menu opens upwards. */
export function UserMenu({ onRestart, compact = false }: { onRestart: () => void; compact?: boolean }) {
  const { runWithLoader } = usePageTransition();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
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
    <div className={`${styles.user} ${compact ? styles.userCompact : ""}`} ref={ref}>
      <button
        className={styles.userButton}
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Аккаунт"
        onClick={() => setOpen((v) => !v)}
      >
        <img className={styles.userAvatar} src="/assets/avatar.svg" alt="" />
        {!compact && (
          <>
            <span className={styles.userName}>user_name</span>
            <img className={styles.userChevron} src="/assets/chevron-down.svg" alt="" />
          </>
        )}
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
  );
}
