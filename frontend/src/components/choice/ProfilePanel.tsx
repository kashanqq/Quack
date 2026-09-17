"use client";

import { useRef, useState } from "react";
import { profileItems, type FieldKey, type Profile, type ProfileItem } from "./assistant";
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
  onEdit: (key: FieldKey, value: string) => void;
};

/**
 * Student profile: what we know and what we assume. The colour of the left bar and of the value
 * tells which is which; any value can be edited in place.
 */
export function ProfilePanel({ profile, readiness, versions, onHide, onEdit }: ProfilePanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const items = profileItems(profile);

  return (
    <div className={styles.profileCard}>
      <div className={styles.profileHead}>
        <h2 className={styles.profileTitle}>Профиль студента</h2>
        <button type="button" className={`${layout.iconButton} ${styles.profileHide}`} aria-label="Скрыть профиль" onClick={onHide}>
          <Icon name="x" className={styles.profileHideMobile} />
          <Icon name="panel-right-close" className={styles.profileHideDesktop} />
        </button>
      </div>
      <div className={styles.profileBody}>
        <div className={styles.profileScroll} ref={scrollRef}>
          <dl className={styles.profileList}>
            {items.map((item) => (
              <ProfileRow key={item.key} item={item} version={versions[item.key] ?? 0} onEdit={onEdit} />
            ))}
          </dl>
        </div>

        <div className={styles.profileFooter}>
          <span className={styles.profileReadinessLabel}>Готовность профиля: {readiness}%</span>
          <div className={styles.progress} role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={readiness}>
            <div className={styles.progressFill} style={{ width: `${readiness}%` }} />
          </div>
        </div>

        <CustomScrollbar target={scrollRef} className={styles.scrollbarPanel} />
      </div>
    </div>
  );
}

/** Clearly labelled button that shows the student profile, with its readiness. */
export function ProfileToggle({
  open,
  readiness,
  onClick,
  className,
}: {
  open: boolean;
  readiness: number;
  onClick: () => void;
  className?: string;
}) {
  return (
    <button
      type="button"
      className={[styles.profileToggle, styles.glass, className].filter(Boolean).join(" ")}
      aria-expanded={open}
      aria-label={`${open ? "Скрыть" : "Показать"} профиль студента, готовность ${readiness}%`}
      onClick={onClick}
    >
      <Icon name="user-round" size={18} />
      <span className={styles.profileToggleLabel}>Профиль</span>
      <span className={styles.profileToggleMeter} aria-hidden="true">
        <span style={{ width: `${readiness}%` }} />
      </span>
      <span className={styles.profileToggleValue}>{readiness}%</span>
    </button>
  );
}

function ProfileRow({ item, version, onEdit }: { item: ProfileItem; version: number; onEdit: ProfilePanelProps["onEdit"] }) {
  const [draft, setDraft] = useState<string | null>(null);
  // Closing the input also blurs it: this keeps Enter/Escape from being followed by a second save
  const closed = useRef(true);

  const start = () => {
    closed.current = false;
    setDraft(item.value);
  };

  const finish = (commit: boolean) => {
    if (closed.current || draft === null) return;
    closed.current = true;
    if (commit && draft.trim() !== item.value) onEdit(item.key, draft);
    setDraft(null);
  };

  return (
    <div className={`${styles.profileRow} ${version ? styles.isUpdated : ""}`} data-status={item.status}>
      <dt>{item.label}</dt>
      {draft !== null ? (
        <dd>
          <input
            autoFocus
            onFocus={(e) => e.target.select()}
            className={styles.profileInput}
            value={draft}
            aria-label={item.label}
            placeholder={item.key === "soft" ? "Через запятую" : undefined}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={() => finish(true)}
            onKeyDown={(e) => {
              if (e.key === "Enter") finish(true);
              if (e.key === "Escape") {
                e.stopPropagation();
                finish(false);
              }
            }}
          />
        </dd>
      ) : (
        // Re-keying replays the highlight animation on every change
        <dd key={version}>
          <button
            type="button"
            className={styles.profileValue}
            aria-label={`Изменить: ${item.label}`}
            onClick={start}
          >
            {item.chips ? (
              <span className={styles.profileChips}>
                {item.chips.map((chip) => (
                  <span key={chip}>{chip}</span>
                ))}
              </span>
            ) : (
              <span>{item.value}</span>
            )}
            <Icon name="pencil" size={16} className={styles.profileEditIcon} />
          </button>
        </dd>
      )}
    </div>
  );
}
