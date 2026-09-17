"use client";

import { useState } from "react";
import { Icon } from "../choice/Icon";
import {
  AREAS,
  day,
  formatDate,
  formatShort,
  forecastSeries,
  SET_STATUS_LABEL,
  SETS,
  skillById,
  SKILLS,
  STATE_LABEL,
  TODAY,
} from "./prepData";
import { closed, disputeMisconception, MISCONCEPTION_LABEL, readiness, setStatus, type PrepModel } from "./prepModel";
import { SkillGraph, StateGlyph, StateLegend } from "./SkillGraph";
import styles from "./prep.module.css";

type Props = {
  model: PrepModel;
  onMakeCurrent: (setId: string) => void;
  onModel: (model: PrepModel) => void;
};

const STATUS_TEXT = { ...SET_STATUS_LABEL, proposed: "предложен" };

/** §4.3: the route of sets by date and by area, plus the knowledge map they are built from. */
export function SetsView({ model, onMakeCurrent, onModel }: Props) {
  const [selected, setSelected] = useState<string | null>("circle");
  const { forecast } = forecastSeries(readiness(model), model.extraDays);
  const testDate = day(11, 7);
  const current = SETS.find((s) => s.id === model.currentSet);

  // Route timeline scale
  const start = day(9, 1).getTime();
  const end = day(11, 12).getTime();
  const pct = (d: Date) => `${((d.getTime() - start) / (end - start)) * 100}%`;

  const skill = selected ? skillById(selected) : null;

  return (
    <div className={styles.canvasGrid}>
      {/* Route by date */}
      <section className={`${styles.canvas} ${styles.full}`} aria-label="Маршрут">
        <header className={styles.canvasHead}>
          <h3>SAT Math · маршрут</h3>
          <span className={forecast <= testDate ? styles.ok : styles.warn}>
            прогноз готовности {formatDate(forecast)} · тест {formatDate(testDate)}
          </span>
        </header>
        <div className={styles.route}>
          <div className={styles.routeAxis} aria-hidden="true">
            {[day(9, 1), day(10, 1), day(11, 1)].map((m) => (
              <span key={m.getTime()} style={{ left: pct(m) }}>
                {formatShort(m).replace(/^\d+ /, "")}
              </span>
            ))}
          </div>
          <div className={styles.routeRows}>
            <div className={styles.routeMarkers} aria-hidden="true">
              <span className={styles.routeToday} style={{ left: pct(TODAY) }}>
                <span>сегодня</span>
              </span>
              <span className={styles.routeTest} style={{ left: pct(testDate) }}>
                <span>тест</span>
              </span>
              <span className={styles.routeForecast} style={{ left: pct(forecast) }}>
                <span>прогноз</span>
              </span>
            </div>
            {SETS.map((set) => {
              const status = setStatus(model, set);
              return (
                <div key={set.id} className={styles.routeRow}>
                  <span className={styles.routeLabel}>
                    {set.number}. {set.title}
                  </span>
                  <span className={styles.routeTrack}>
                    <span
                      className={styles.routeBar}
                      data-status={status}
                      style={{ left: pct(set.start), width: `calc(${pct(set.deadline)} - ${pct(set.start)})` }}
                      title={`${set.title}: ${formatShort(set.start)} – ${formatShort(set.deadline)}, ${STATUS_TEXT[status]}`}
                    />
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Knowledge map */}
      <section className={`${styles.canvas} ${styles.full}`} aria-label="Карта навыков">
        <header className={styles.canvasHead}>
          <h3>Карта навыков</h3>
          <StateLegend />
        </header>
        <div className={styles.mapLayout}>
          <SkillGraph
            states={model.states}
            recall={model.recall}
            misconceptions={model.misconceptions}
            highlight={current?.skills ?? []}
            selected={selected}
            onSelect={(id) => setSelected((s) => (s === id ? null : id))}
          />

          <aside className={styles.skillPanel} aria-live="polite">
            {skill ? (
              <>
                <p className={styles.eyebrow}>{skill.area}</p>
                <h4>{skill.name}</h4>
                <p className={styles.skillState}>
                  <StateGlyph state={model.states[skill.id]} size={16} />
                  {STATE_LABEL[model.states[skill.id]]} · вспомнит сейчас ~{Math.round(model.recall[skill.id] * 100)}% · вес{" "}
                  {skill.weight}%
                </p>
                {skill.root && <p className={styles.rootNote}>Корень: ошибки в «{SKILLS.filter((s) => s.requires.includes(skill.id)).map((s) => s.name).join(", ")}» идут отсюда.</p>}
                <dl className={styles.facts}>
                  <div>
                    <dt>Опирается на</dt>
                    <dd>{skill.requires.map((id) => skillById(id).name).join(", ") || "—"}</dd>
                  </div>
                  <div>
                    <dt>Нужен для</dt>
                    <dd>
                      {SKILLS.filter((s) => s.requires.includes(skill.id))
                        .map((s) => s.name)
                        .join(", ") || "—"}
                    </dd>
                  </div>
                  <div>
                    <dt>В сетах</dt>
                    <dd>
                      {SETS.filter((s) => s.skills.includes(skill.id))
                        .map((s) => `сет ${s.number}`)
                        .join(", ") || "—"}
                    </dd>
                  </div>
                </dl>

                {model.misconceptions[skill.id].length > 0 && (
                  <>
                    <p className={styles.eyebrow}>Ловушки</p>
                    <ul className={styles.plainList}>
                      {model.misconceptions[skill.id].map((m) => (
                        <li key={m.id} className={styles.misconception} data-status={m.status}>
                          <span>
                            {m.text}
                            {m.trigger && <span className={styles.muted}> · {m.trigger}</span>}
                          </span>
                          <span className={styles.muted}>{MISCONCEPTION_LABEL(m)}</span>
                          {(m.status === "confirmed" || m.status === "suspected") && (
                            <button
                              type="button"
                              className={styles.link}
                              onClick={() => onModel(disputeMisconception(model, skill.id, m.id))}
                            >
                              Не согласен
                            </button>
                          )}
                        </li>
                      ))}
                    </ul>
                  </>
                )}

                <p className={styles.eyebrow}>Откуда мы это знаем</p>
                {model.evidence[skill.id].length ? (
                  <ul className={styles.evidence}>
                    {model.evidence[skill.id].map((e, i) => (
                      <li key={i}>
                        <span className={styles.sourceTag}>{e.source}</span>
                        <span>{e.text}</span>
                        <span className={styles.muted}>{formatShort(e.date)}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className={styles.muted}>Свидетельств пока нет — навык проверится короткой серией внутри сета.</p>
                )}
              </>
            ) : (
              <p className={styles.muted}>Выбери навык на карте, чтобы увидеть его состояние, ловушки и откуда мы это знаем.</p>
            )}
          </aside>
        </div>
      </section>

      {/* Sets by area */}
      <section className={`${styles.canvas} ${styles.full}`} aria-label="Все сеты">
        <header className={styles.canvasHead}>
          <h3>Все сеты по областям</h3>
          <span className={styles.muted}>текущий можно сменить — прогноз пересчитается</span>
        </header>
        <div className={styles.areaGroups}>
          {AREAS.map((area) => {
            const sets = SETS.filter((s) => s.area === area);
            if (!sets.length) return null;
            return (
              <div key={area} className={styles.areaGroup}>
                <p className={styles.eyebrow}>{area}</p>
                {sets.map((set) => {
                  const status = setStatus(model, set);
                  return (
                    <article key={set.id} className={styles.setCard} data-status={status}>
                      <div className={styles.setHead}>
                        <strong>
                          Сет {set.number} · {set.title}
                        </strong>
                        <span className={styles.statusPill} data-status={status}>
                          {STATUS_TEXT[status]}
                        </span>
                      </div>
                      <span className={styles.muted}>
                        {formatShort(set.start)} – {formatShort(set.deadline)} · закрыто {closed(model, set)} из {set.skills.length}
                      </span>
                      <ul className={styles.skillChips}>
                        {set.skills.map((id) => (
                          <li key={id}>
                            <StateGlyph state={model.states[id]} size={12} />
                            {skillById(id).name}
                          </li>
                        ))}
                      </ul>
                      <p className={styles.why}>Почему в маршруте: {set.why}</p>
                      {status !== "current" && (
                        <button type="button" className={styles.secondary} onClick={() => onMakeCurrent(set.id)}>
                          <Icon name="target" size={16} />
                          {status === "done" ? "Вернуться к сету" : "Сделать текущим"}
                        </button>
                      )}
                    </article>
                  );
                })}
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
