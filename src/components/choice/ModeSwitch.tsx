"use client";

import { useLayoutEffect, useRef } from "react";
import styles from "./choice.module.css";

export type Mode = "choice" | "prep";

const TABS: { mode: Mode; label: string }[] = [
  { mode: "choice", label: "Choice" },
  { mode: "prep", label: "Preparation" },
];

/** Choice / Preparation tabs with a pill that slides under the active one. */
export function ModeSwitch({ mode, onChange }: { mode: Mode; onChange: (mode: Mode) => void }) {
  const pillRef = useRef<HTMLSpanElement>(null);
  const tabRefs = useRef<Record<Mode, HTMLButtonElement | null>>({ choice: null, prep: null });

  useLayoutEffect(() => {
    const place = () => {
      const tab = tabRefs.current[mode];
      if (!tab || !pillRef.current) return;
      pillRef.current.style.width = `${tab.offsetWidth}px`;
      pillRef.current.style.transform = `translateX(${tab.offsetLeft}px)`;
    };
    place();
    document.fonts.ready.then(place);
    window.addEventListener("resize", place);
    return () => window.removeEventListener("resize", place);
  }, [mode]);

  return (
    <div className={styles.modeSwitch} role="tablist" aria-label="Раздел">
      <span ref={pillRef} className={styles.modePill} aria-hidden="true" />
      {TABS.map((tab) => (
        <button
          key={tab.mode}
          ref={(el) => {
            tabRefs.current[tab.mode] = el;
          }}
          className={`${styles.modeTab} ${mode === tab.mode ? styles.isActive : ""}`}
          type="button"
          role="tab"
          aria-selected={mode === tab.mode}
          onClick={() => onChange(tab.mode)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
