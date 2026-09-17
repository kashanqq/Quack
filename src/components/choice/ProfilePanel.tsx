"use client";

import { useRef } from "react";
import { FIELDS, fieldValue, type FieldKey, type Profile } from "./assistant";
import { CustomScrollbar } from "./CustomScrollbar";
import { Icon } from "./Icon";
import styles from "./choice.module.css";
import layout from "./layout.module.css";

type ProfilePanelProps = {
  profile: Profile;
  readiness: number;
  /** Bumped per field whenever its value changes, to replay the highlight */
  versions: Partial<Record<FieldKey, number>>;
  onHide: () => void;
};

/** "Как я тебя вижу" — what the assistant has understood so far, with profile readiness. */
export function ProfilePanel({ profile, readiness, versions, onHide }: ProfilePanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const rows = FIELDS.map(([key, label]) => ({ key, label, value: fieldValue(profile, key) })).filter((r) => r.value);

  return (
    <div className={styles.profileCard}>
      <div className={styles.profileHead}>
        <h2 className={styles.profileTitle}>Как я тебя вижу:</h2>
        <button type="button" className={`${layout.iconButton} ${styles.profileHide}`} aria-label="Скрыть панель" onClick={onHide}>
          <Icon name="panel-right-close" />
        </button>
      </div>
      <div className={styles.profileBody}>
        <div className={styles.profileScroll} ref={scrollRef}>
          {rows.length ? (
            <dl className={styles.profileList}>
              {rows.map(({ key, label, value }) => (
                <div key={key} className={`${styles.profileRow} ${versions[key] ? styles.isUpdated : ""}`}>
                  <dt>{label}</dt>
                  {/* Re-keying replays the highlight animation on every change */}
                  <dd key={versions[key] ?? 0}>{value}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className={styles.profileEmpty}>Пока пусто — пиши в чат, я всё запишу.</p>
          )}
        </div>

        <div className={styles.profileFooter}>
          <span className={styles.profileReadinessLabel}>Готовность профиля:</span>
          <div className={styles.progress} role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={readiness}>
            <div className={styles.progressFill} style={{ width: `${readiness}%` }} />
          </div>
        </div>

        <CustomScrollbar target={scrollRef} className={styles.scrollbarPanel} />
      </div>
    </div>
  );
}
