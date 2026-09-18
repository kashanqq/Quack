"use client";

import { formatShort } from "../prep/prepData";
import { streak, type ActivityDay } from "./dashboardRules";
import styles from "./dashboard.module.css";

/** Five weeks of activity: tasks, mocks and conversations, one square per day. */
export function ActivityGrid({ days }: { days: ActivityDay[] }) {
  const total = days.reduce((sum, d) => sum + d.count, 0);
  const row = streak(days);

  return (
    <section className={styles.card} aria-label="Активность">
      <header className={styles.cardHead}>
        <h3>Активность</h3>
        <span className={styles.muted}>
          {total} действ{total % 10 === 1 && total % 100 !== 11 ? "ие" : "ий"} за месяц
          {row > 0 && ` · ${row} дн. подряд`}
        </span>
      </header>

      <div className={styles.activity}>
        {days.map((d) => (
          <span
            key={d.date.toISOString()}
            className={styles.activityDay}
            data-level={d.level}
            title={`${formatShort(d.date)}: ${d.count ? d.parts.join(", ") : "ничего"}`}
          />
        ))}
      </div>

      <div className={styles.activityFoot}>
        <span className={styles.muted}>{formatShort(days[0].date)}</span>
        <span className={styles.activityScale}>
          меньше
          {[0, 1, 2, 3].map((level) => (
            <span key={level} className={styles.activityDay} data-level={level} aria-hidden="true" />
          ))}
          больше
        </span>
        <span className={styles.muted}>сегодня</span>
      </div>

      <table className={styles.srOnly}>
        <caption>Действия по дням</caption>
        <tbody>
          {days
            .filter((d) => d.count > 0)
            .map((d) => (
              <tr key={d.date.toISOString()}>
                <td>{formatShort(d.date)}</td>
                <td>{d.parts.join(", ")}</td>
              </tr>
            ))}
        </tbody>
      </table>
    </section>
  );
}
