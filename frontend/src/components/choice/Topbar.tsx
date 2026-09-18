"use client";

import { Duck } from "@/components/duck/Duck";
import { Icon, type IconName } from "./Icon";
import { ProfileToggle } from "./ProfilePanel";
import type { Mode } from "./Sidebar";
import styles from "./choice.module.css";
import layout from "./layout.module.css";

type TopbarProps = {
  mode: Mode;
  onMode: (mode: Mode) => void;
  /** Opens the left column (programs, chats, account) on phones */
  onOpenMenu: () => void;
  /** Toggle for the student profile; omitted while it isn't available */
  profilePanel?: { open: boolean; readiness: number; onToggle: () => void };
  /** Something changed or a date is close: a red dot sits on the Q */
  alert?: { active: boolean; reasons: string[] };
};

const MODES: { mode: Mode; label: string; icon: IconName }[] = [
  { mode: "choice", label: "Выбор", icon: "graduation-cap" },
  { mode: "prep", label: "Подготовка", icon: "book-open-check" },
];

/** Выбор · Quack! · Подготовка — the logo in the middle opens the dashboard. */
const LETTERS = [..."Quack"];

export function Topbar({ mode, onMode, onOpenMenu, profilePanel, alert }: TopbarProps) {
  return (
    <header className={styles.topbar}>
      <div className={styles.topbarSide}>
        <button type="button" className={`${layout.iconButton} ${styles.menuButton} ${styles.glass}`} aria-label="Меню: программы и чаты" onClick={onOpenMenu}>
          <Icon name="menu" />
        </button>
      </div>

      <div className={styles.modeSwitch} role="tablist" aria-label="Раздел">
        <button
          type="button"
          role="tab"
          aria-selected={mode === "choice"}
          className={`${styles.modeButton} ${styles.glass}`}
          title={MODES[0].label}
          onClick={() => onMode("choice")}
        >
          <Icon name={MODES[0].icon} size={18} />
          <span className={styles.modeLabel}>{MODES[0].label}</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={mode === "dashboard"}
          className={styles.topbarLogo}
          title={alert?.active ? `Дашборд · ${alert.reasons[0]}` : "Дашборд"}
          onClick={() => onMode("dashboard")}
        >
          <span className={styles.logoLetters}>
            {LETTERS.map((letter, i) => (
              <span key={i} className={styles.letter} style={{ animationDelay: `${i * 70}ms` }}>
                {letter}
                {i === 0 && alert?.active && (
                  <span className={styles.logoDot} role="status" aria-label={`Есть важное: ${alert.reasons.join("; ")}`} />
                )}
              </span>
            ))}
            <span className={`${styles.letter} ${styles.accent}`} style={{ animationDelay: `${LETTERS.length * 70}ms` }}>
              !
            </span>
          </span>
          {/* The duck walks along the wordmark while the dashboard is open */}
          {mode === "dashboard" && (
            <span className={styles.logoTrack} aria-hidden="true">
              <span className={styles.logoDuck}>
                <span>
                  <Duck />
                </span>
              </span>
            </span>
          )}
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={mode === "prep"}
          className={`${styles.modeButton} ${styles.glass}`}
          title={MODES[1].label}
          onClick={() => onMode("prep")}
        >
          <Icon name={MODES[1].icon} size={18} />
          <span className={styles.modeLabel}>{MODES[1].label}</span>
        </button>
      </div>

      <div className={`${styles.topbarSide} ${styles.topbarRight}`}>
        {profilePanel && (
          <ProfileToggle
            open={profilePanel.open}
            readiness={profilePanel.readiness}
            onClick={profilePanel.onToggle}
          />
        )}
      </div>
    </header>
  );
}
