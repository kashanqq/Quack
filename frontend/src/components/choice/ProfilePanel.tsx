"use client";

import { useRef, useState } from "react";
import { PixelDuck } from "@/components/duck/PixelDuck";
import { FIELDS, profileItems, type FieldKey, type FieldStatus, type Profile, type ProfileItem } from "./assistant";
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

/** The passport is read in blocks, so a student sees at a glance which part of them is still blank. */
const GROUPS: { title: string; keys: FieldKey[] }[] = [
  { title: "Учёба", keys: ["grade", "direction", "location", "language"] },
  { title: "Экзамены", keys: ["ielts", "sat", "ent"] },
  { title: "Деньги", keys: ["budget", "grant"] },
  { title: "О тебе", keys: ["strong", "soft"] },
];

/** Fields that make the one-line summary under the title, first known wins; bare values get a word. */
const SUMMARY: [FieldKey, (value: string) => string][] = [
  ["direction", (v) => v],
  ["location", (v) => v],
  ["grade", (v) => v],
  ["ielts", (v) => `IELTS ${v}`],
  ["grant", (v) => `грант: ${v.toLowerCase()}`],
];

type Row = Omit<ProfileItem, "status"> & { status: FieldStatus | "empty" };

const labelOf = (key: FieldKey) => FIELDS.find(([k]) => k === key)![1];

/**
 * Student profile as a passport: a duck, the readiness ring and a one-line summary on top, then the
 * fields in blocks. Said and assumed values are told apart by colour; a guess is confirmed with one
 * press, a blank field is a dashed slot to fill in. Any value can be edited in place.
 */
export function ProfilePanel({ profile, readiness, versions, onHide, onEdit }: ProfilePanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const items = profileItems(profile);
  const byKey = new Map(items.map((item) => [item.key, item]));
  const summary = SUMMARY.flatMap(([key, word]) => {
    const value = byKey.get(key)?.value;
    return value ? [word(value)] : [];
  })
    .slice(0, 3)
    .join(" · ");

  return (
    <div className={styles.profileCard}>
      <div className={`${styles.profileHead} ${styles.passHead}`}>
        <Ring value={readiness} />
        <div className={styles.passTitleBox}>
          <h2 className={styles.passTitle}>Профиль</h2>
          <p className={styles.passSummary}>{summary || "Расскажи о себе в чате — я запишу сюда"}</p>
        </div>
        {/* Asleep while the profile is empty, waving once it is complete */}
        <span className={styles.passDuck} aria-hidden="true">
          <PixelDuck tempo="chill" asleep={readiness === 0} waving={readiness === 100} />
        </span>
        <button type="button" className={`${layout.iconButton} ${styles.profileHide}`} aria-label="Скрыть профиль" onClick={onHide}>
          <Icon name="x" className={styles.profileHideMobile} />
          <Icon name="panel-right-close" className={styles.profileHideDesktop} />
        </button>
      </div>
      <div className={styles.profileBody}>
        <div className={styles.profileScroll} ref={scrollRef}>
          {GROUPS.map((group) => (
            <section key={group.title} className={styles.passGroup} aria-label={group.title}>
              <h3 className={styles.passGroupTitle}>{group.title}</h3>
              <dl className={styles.profileList}>
                {group.keys.map((key) => {
                  const row: Row = byKey.get(key) ?? { key, label: labelOf(key), value: "", status: "empty" };
                  return <ProfileRow key={key} row={row} profile={profile} version={versions[key] ?? 0} onEdit={onEdit} />;
                })}
              </dl>
            </section>
          ))}
        </div>

        <p className={styles.passLegend}>
          <span data-status="said">сказал ты</span>
          <span data-status="assumed">догадка — нажми «верно»</span>
        </p>

        <CustomScrollbar target={scrollRef} className={styles.scrollbarPanel} />
      </div>
    </div>
  );
}

/** Profile readiness as a ring with the percentage inside. */
function Ring({ value }: { value: number }) {
  const r = 22;
  const length = 2 * Math.PI * r;
  return (
    <div className={styles.passRing} role="img" aria-label={`Профиль заполнен на ${value}%`}>
      <svg viewBox="0 0 52 52" aria-hidden="true">
        <circle cx="26" cy="26" r={r} className={styles.passRingTrack} />
        <circle
          cx="26"
          cy="26"
          r={r}
          className={styles.passRingFill}
          strokeDasharray={length}
          strokeDashoffset={length * (1 - value / 100)}
        />
      </svg>
      <span>{value}%</span>
    </div>
  );
}

function ProfileRow({
  row,
  profile,
  version,
  onEdit,
}: {
  row: Row;
  profile: Profile;
  version: number;
  onEdit: ProfilePanelProps["onEdit"];
}) {
  const [draft, setDraft] = useState<string | null>(null);
  // Closing the input also blurs it: this keeps Enter/Escape from being followed by a second save
  const closed = useRef(true);

  const start = () => {
    closed.current = false;
    setDraft(row.value);
  };

  const finish = (commit: boolean) => {
    if (closed.current || draft === null) return;
    closed.current = true;
    if (commit && draft.trim() && draft.trim() !== row.value) onEdit(row.key, draft);
    setDraft(null);
  };

  // «IELTS 6.0 — пока не сдавал» is our reading of something the student did say, not a bare guess
  const confirmable = row.status === "assumed" && !(row.key === "ielts" && profile.ielts);

  return (
    <div className={`${styles.profileRow} ${version ? styles.isUpdated : ""}`} data-status={row.status}>
      <dt>{row.label}</dt>
      {draft !== null ? (
        <dd>
          <input
            autoFocus
            onFocus={(e) => e.target.select()}
            className={styles.profileInput}
            value={draft}
            aria-label={row.label}
            placeholder={row.key === "soft" ? "Через запятую" : undefined}
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
        <dd key={version} className={styles.passValueCell}>
          {row.status === "empty" ? (
            <button type="button" className={styles.passSlot} aria-label={`Добавить: ${row.label}`} onClick={start}>
              <Icon name="plus" size={14} /> добавить
            </button>
          ) : (
            <button type="button" className={styles.profileValue} aria-label={`Изменить: ${row.label}`} onClick={start}>
              {row.chips ? (
                <span className={styles.profileChips}>
                  {row.chips.map((chip) => (
                    <span key={chip}>{chip}</span>
                  ))}
                </span>
              ) : (
                <span>{row.value}</span>
              )}
              <Icon name="pencil" size={16} className={styles.profileEditIcon} />
            </button>
          )}
          {confirmable && (
            <button
              type="button"
              className={styles.passConfirm}
              aria-label={`Верно: ${row.label} — ${row.value}`}
              onClick={() => onEdit(row.key, row.value)}
            >
              <Icon name="check" size={14} /> верно
            </button>
          )}
        </dd>
      )}
    </div>
  );
}
