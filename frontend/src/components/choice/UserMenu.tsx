"use client";

import { useEffect, useRef, useState } from "react";
import { usePageTransition } from "@/components/transition/TransitionProvider";
import { TransitionLink } from "@/components/transition/TransitionLink";
import { DEMO_SHIFT, shiftDemoClock } from "../prep/prepData";
import { Icon } from "./Icon";
import styles from "./choice.module.css";

type Props = {
  onRestart: () => void;
  /** The student profile opens from the avatar and the name, in every section */
  profile: { open: boolean; readiness: number; onToggle: () => void };
  compact?: boolean;
};

/**
 * The bottom of the left column: the avatar and the name open the student profile; the gear beside them
 * opens the account menu, which opens upwards. In the icon rail the two stack.
 */
export function UserMenu({ onRestart, profile, compact = false }: Props) {
  const { runWithLoader } = usePageTransition();
  const [open, setOpen] = useState(false);
  // Read after mount: the server renders day zero, and the menu is in the markup from the start
  const [shift, setShift] = useState(0);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => setShift(DEMO_SHIFT), []);

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
      <div className={styles.userRow}>
        <button
          className={styles.userButton}
          type="button"
          aria-expanded={profile.open}
          aria-label={`${profile.open ? "Скрыть" : "Показать"} профиль студента, заполнен на ${profile.readiness}%`}
          title={`Профиль студента · заполнен на ${profile.readiness}%`}
          onClick={profile.onToggle}
        >
          <img className={styles.userAvatar} src="/assets/avatar.svg" alt="" />
          {!compact && (
            <span className={styles.userText}>
              <span className={styles.userName}>user_name</span>
              {/* How full the profile is — the number lives in the tooltip */}
              <span className={styles.userMeter} aria-hidden="true">
                <span style={{ width: `${profile.readiness}%` }} />
              </span>
            </span>
          )}
        </button>
        <button
          className={styles.userSettings}
          type="button"
          aria-haspopup="menu"
          aria-expanded={open}
          aria-label="Аккаунт и настройки"
          title="Аккаунт и настройки"
          onClick={() => setOpen((v) => !v)}
        >
          <Icon name="settings" size={18} />
        </button>
      </div>
      <div className={`${styles.userMenu} ${open ? styles.isOpen : ""}`} role="menu">
        {/* Account settings come later; the item marks where they will live */}
        <button type="button" role="menuitem" disabled>
          Настройки аккаунта · скоро
        </button>
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
        {/* Demo only: move the clock to watch deadlines come up, pass and light up Quack */}
        <button type="button" role="menuitem" onClick={() => shiftDemoClock(7, "демо: прошла неделя")}>
          Демо: неделя вперёд{shift ? ` · сейчас +${shift} дн.` : ""}
        </button>
        {shift > 0 && (
          <button type="button" role="menuitem" onClick={() => shiftDemoClock(null, "демо: время вернулось")}>
            Демо: вернуть сегодня
          </button>
        )}
        <TransitionLink role="menuitem" href="/">
          Выйти
        </TransitionLink>
      </div>
    </div>
  );
}
