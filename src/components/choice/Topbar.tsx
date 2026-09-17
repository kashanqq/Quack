"use client";

import { useEffect, useRef, useState } from "react";
import { usePageTransition } from "@/components/transition/TransitionProvider";
import { TransitionLink } from "@/components/transition/TransitionLink";
import styles from "./choice.module.css";

export function Topbar({ onRestart }: { onRestart: () => void }) {
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
    </header>
  );
}
