"use client";

import type { Profile } from "./assistant";
import { Icon } from "./Icon";
import { compareRows, compareSummary, programById } from "./programs";
import styles from "./layout.module.css";

type CompareViewProps = {
  ids: string[];
  profile: Profile;
  onBack: () => void;
  onRemove: (id: string) => void;
  onOpen: (id: string) => void;
};

/** Side-by-side comparison (§3.4): rows that differ are marked, then a short takeaway. */
export function CompareView({ ids, profile, onBack, onRemove, onOpen }: CompareViewProps) {
  const rows = compareRows(ids, profile);
  const { same, keyDifferences } = compareSummary(rows);

  return (
    <section className={styles.compare} aria-label="Сравнение программ">
      <div className={styles.compareHead}>
        <button type="button" className={styles.iconButton} aria-label="Назад к чату" onClick={onBack}>
          <Icon name="arrow-left" />
        </button>
        <h2 className={styles.compareTitle}>Сравнение</h2>
      </div>

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th />
              {ids.map((id) => {
                const p = programById(id);
                return (
                  <th key={id} scope="col">
                    <div className={styles.colHead}>
                      <button type="button" className={styles.rowMain} style={{ padding: 0 }} onClick={() => onOpen(id)}>
                        <span>
                          <span className={styles.colName}>{p.university}</span>
                          <span className={styles.colSub}>{p.program}</span>
                        </span>
                      </button>
                      <button type="button" className={styles.iconButton} aria-label="Убрать из сравнения" onClick={() => onRemove(id)}>
                        <Icon name="x" size={16} />
                      </button>
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={row.label} className={row.differs ? styles.differs : ""} style={{ animationDelay: `${i * 35}ms` }}>
                <th scope="row">{row.label}</th>
                {row.values.map((value, j) => (
                  <td key={ids[j]}>{value}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className={styles.compareSummary}>
        {same.length > 0 && <>Одинаково по: {same.join(", ")}. </>}
        {keyDifferences.length > 0 ? (
          <>Для тебя разница — {keyDifferences.join(", ")}.</>
        ) : (
          <>Существенных для тебя различий нет.</>
        )}
      </p>
    </section>
  );
}
