"use client";

import { useState } from "react";
import { Icon } from "../choice/Icon";
import { daysBetween, formatDate, TODAY } from "../prep/prepData";
import { downloadIcs, googleCalendarUrl } from "./calendarExport";
import { monthGrid, sameDay, type CalendarEvent } from "./dashboardRules";
import styles from "./dashboard.module.css";

const MONTHS = [
  "Январь",
  "Февраль",
  "Март",
  "Апрель",
  "Май",
  "Июнь",
  "Июль",
  "Август",
  "Сентябрь",
  "Октябрь",
  "Ноябрь",
  "Декабрь",
];
const WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

const KIND_LABEL = { registration: "регистрация", test: "тест", application: "подача" } as const;

type Marks = {
  /** The milestone an event is, when it can be ticked done */
  idOf: (event: CalendarEvent) => string | undefined;
  done: string[];
  onToggle: (milestone: string) => void;
};

/**
 * Deadlines as a month calendar: registrations, tests and applications. It is also the list of milestones:
 * each one is ticked done here, and unticked if it was a mistake (product-logic §4.1).
 */
export function CalendarTab({
  events,
  marks,
  onPickDate,
}: {
  events: CalendarEvent[];
  marks: Marks;
  /** Another sitting of SAT or ЕНТ becomes the one the plan works to */
  onPickDate: (exam: "sat" | "ent", key: string) => void;
}) {
  // Open on this month, or on the month of the next event when this one is empty
  const [cursor, setCursor] = useState(() => {
    const thisMonth = events.some((e) => e.date.getFullYear() === TODAY.getFullYear() && e.date.getMonth() === TODAY.getMonth());
    const upcoming = events.find((e) => e.date >= TODAY);
    const base = thisMonth || !upcoming ? TODAY : upcoming.date;
    return { year: base.getFullYear(), month: base.getMonth() };
  });
  const [selected, setSelected] = useState<Date | null>(null);

  const cells = monthGrid(cursor.year, cursor.month);
  const eventsOn = (d: Date) => events.filter((e) => sameDay(e.date, d));
  const monthEvents = events
    .filter((e) => e.date.getFullYear() === cursor.year && e.date.getMonth() === cursor.month)
    .sort((a, b) => a.date.getTime() - b.date.getTime());
  const shown = selected ? eventsOn(selected) : monthEvents;

  const step = (delta: number) => {
    const d = new Date(cursor.year, cursor.month + delta, 1);
    setCursor({ year: d.getFullYear(), month: d.getMonth() });
    setSelected(null);
  };

  return (
    <section className={styles.card} aria-label="Календарь">
      <header className={styles.cardHead}>
        <h3>
          {MONTHS[cursor.month]} {cursor.year}
        </h3>
        <div className={styles.calNav}>
          <button
            type="button"
            className={styles.addToCalendar}
            title="Скачает файл .ics со всеми датами — открывается в Google Календаре, Apple и Outlook"
            onClick={() => downloadIcs(events.filter((e) => !e.alternative))}
          >
            <Icon name="calendar-plus" size={16} /> В свой календарь
          </button>
          <ul className={styles.calLegend}>
            <li data-kind="registration">регистрация</li>
            <li data-kind="test">тест</li>
            <li data-kind="application">подача</li>
          </ul>
          <button type="button" className={styles.navButton} aria-label="Предыдущий месяц" onClick={() => step(-1)}>
            <Icon name="arrow-left" size={16} />
          </button>
          <button type="button" className={styles.navButton} aria-label="Следующий месяц" onClick={() => step(1)}>
            <Icon name="arrow-left" size={16} className={styles.flip} />
          </button>
        </div>
      </header>

      <div className={styles.calendar} role="grid">
        {WEEKDAYS.map((w) => (
          <span key={w} className={styles.calWeekday}>
            {w}
          </span>
        ))}
        {cells.map((date) => {
          const list = eventsOn(date);
          const outside = date.getMonth() !== cursor.month;
          return (
            <button
              key={date.toISOString()}
              type="button"
              className={styles.calDay}
              data-outside={outside}
              data-today={sameDay(date, TODAY)}
              aria-pressed={selected ? sameDay(date, selected) : false}
              aria-label={`${date.getDate()} ${MONTHS[date.getMonth()].toLowerCase()}${list.length ? `, событий: ${list.length}` : ""}`}
              onClick={() => setSelected((s) => (s && sameDay(s, date) ? null : date))}
            >
              <span className={styles.calNumber}>{date.getDate()}</span>
              {list.length > 0 && (
                <span className={styles.calDots}>
                  {list.slice(0, 3).map((e) => {
                    const id = marks.idOf(e);
                    const done = Boolean(id && marks.done.includes(id));
                    return (
                      <span
                        key={e.id}
                        data-kind={e.kind}
                        data-done={done}
                        data-alt={Boolean(e.alternative)}
                        title={done ? `${e.title} · сделано` : e.alternative ? `${e.title} · другая дата` : e.title}
                      />
                    );
                  })}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div className={styles.calList}>
        <p className={styles.eyebrow}>
          {selected ? formatDate(selected) : `Весь ${MONTHS[cursor.month].toLowerCase()}`}
          {selected && (
            <button type="button" className={styles.link} onClick={() => setSelected(null)}>
              показать весь месяц
            </button>
          )}
        </p>
        {shown.length === 0 ? (
          <p className={styles.muted}>Ничего не запланировано.</p>
        ) : (
          <ul className={styles.calEvents}>
            {shown.map((e) => {
              const left = daysBetween(TODAY, e.date);
              const id = marks.idOf(e);
              const done = Boolean(id && marks.done.includes(id));
              return (
                <li key={e.id} data-done={done} data-alt={Boolean(e.alternative)}>
                  <span className={styles.calKind} data-kind={e.kind}>
                    {KIND_LABEL[e.kind]}
                  </span>
                  <span>
                    <strong>{e.title}</strong>
                    <span className={styles.muted}> · {e.detail}</span>
                  </span>
                  <span className={styles.muted}>
                    {formatDate(e.date)}
                    {done ? " · сделано" : left >= 0 ? ` · через ${left} дн.` : " · прошло"}
                  </span>
                  {e.alternative ? (
                    <button
                      type="button"
                      className={styles.markButton}
                      title="Подготовка, вехи и прогноз пересчитаются под эту дату"
                      onClick={() => onPickDate(e.alternative!.exam, e.alternative!.key)}
                    >
                      <Icon name="calendar-days" size={14} />
                      Сдаю в эту дату
                    </button>
                  ) : id ? (
                    <button
                      type="button"
                      className={styles.markButton}
                      aria-pressed={done}
                      title={done ? "Снять отметку, если это ошибка" : "Отметить, что это уже сделано"}
                      onClick={() => marks.onToggle(id)}
                    >
                      <Icon name="check" size={14} />
                      {done ? "Сделано" : "Отметить"}
                    </button>
                  ) : (
                    <span />
                  )}
                  <a
                    className={styles.googleLink}
                    href={googleCalendarUrl(e)}
                    target="_blank"
                    rel="noreferrer noopener"
                    title="Открыть в Google Календаре"
                    aria-label={`Добавить «${e.title}» в Google Календарь`}
                  >
                    <Icon name="external-link" size={14} />
                    Google
                  </a>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </section>
  );
}
