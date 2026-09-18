"use client";

import { Duck } from "@/components/duck/Duck";
import { Icon, type IconName } from "./Icon";
import type { SignalLevel } from "../quack/contract";
import type { Mode } from "./Sidebar";
import styles from "./choice.module.css";
import layout from "./layout.module.css";

type TopbarProps = {
  mode: Mode;
  onMode: (mode: Mode) => void;
  /** Opens the left column (programs, chats, account) on phones */
  onOpenMenu: () => void;
  /** Something the student has not seen yet: a gradient runs around the button until they open it */
  alert?: { level: SignalLevel | null; reasons: string[] };
};

/** What the menu drawer holds in each section — on phones it is the only way to switch categories */
const MENU_LABEL: Record<Mode, string> = {
  choice: "Меню: программы и чаты",
  prep: "Меню: разделы подготовки",
  dashboard: "Меню: разделы обзора",
};

const MODES: { mode: Mode; label: string; icon: IconName }[] = [
  { mode: "choice", label: "Выбор", icon: "graduation-cap" },
  { mode: "prep", label: "Подготовка", icon: "book-open-check" },
];

/** Выбор · Quack! · Подготовка — the logo in the middle opens the overview. */
const LETTERS = [..."Quack"];

export function Topbar({ mode, onMode, onOpenMenu, alert }: TopbarProps) {
  return (
    <header className={styles.topbar}>
      <div className={styles.topbarSide}>
        <button type="button" className={`${layout.iconButton} ${styles.menuButton} ${styles.glass}`} aria-label={MENU_LABEL[mode]} onClick={onOpenMenu}>
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
          data-alert={alert?.level ?? undefined}
          title={alert?.level ? `Обзор · ${alert.reasons[0]}` : "Обзор: экзамены, дедлайны, календарь"}
          aria-label={alert?.level ? `Обзор. Есть важное: ${alert.reasons.join("; ")}` : "Обзор"}
          onClick={() => onMode("dashboard")}
        >
          <span className={styles.logoLetters}>
            {LETTERS.map((letter, i) => (
              <span key={i} className={styles.letter} style={{ animationDelay: `${i * 70}ms` }}>
                {letter}
              </span>
            ))}
            <span className={`${styles.letter} ${styles.accent}`} style={{ animationDelay: `${LETTERS.length * 70}ms` }}>
              !
            </span>
          </span>
          {/* The duck walks along the top edge of the button while the overview is open */}
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

      {/* Keeps the section switch centred; the profile lives in the left column now */}
      <div className={`${styles.topbarSide} ${styles.topbarRight}`} />
    </header>
  );
}
