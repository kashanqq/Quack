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
import { closed, disputeMisconception, MISCONCEPTION_LABEL, readiness, setStatus, type PrepModel, type PrepSub } from "./prepModel";
import { SkillGraph, StateGlyph, StateLegend } from "./SkillGraph";
import styles from "./prep.module.css";

type Props = {
  model: PrepModel;
  sub: PrepSub;
  onMakeCurrent: (setId: string) => void;
  onModel: (model: PrepModel) => void;
};

const STATUS_TEXT = { ...SET_STATUS_LABEL, proposed: "предложен" };

/**
 * §4.3 — the route of sets and the knowledge map they are built from. Three sub-tabs: the route on a
 * timeline, the map of skills with its evidence, and the full list of sets grouped by area.
 */
export function SetsView({ model, sub, onMakeCurrent, onModel }: Props) {
  if (sub === "map") return <KnowledgeMap model={model} onModel={onModel} />;
  if (sub === "all") return <AllSets model={model} onMakeCurrent={onMakeCurrent} />;
  return <Route model={model} />;
}

/* ---------- Маршрут: the sets on a timeline against the test date ---------- */

const CANVAS_W = 1020;
const CANVAS_H = 286;
const PAD = 54;
const AXIS_Y = 244;
const MID = 140;
const SET_R = 22;

/** Where a set sits on the route: the middle of its window, swaying above and below the line. */
function routeLayout(forecast: Date, testDate: Date) {
  const from = day(9, 1).getTime();
  const to = day(11, 12).getTime();
  const x = (d: Date) => PAD + ((d.getTime() - from) / (to - from)) * (CANVAS_W - PAD * 2);

  const stops = SETS.map((set, i) => ({
    set,
    x: x(new Date((set.start.getTime() + set.deadline.getTime()) / 2)),
    y: MID + (i % 2 ? 30 : -30),
    below: i % 2 === 1,
  }));

  return { x, stops, forecastX: x(forecast), testX: x(testDate) };
}

/** The route as a chain of circles: the same marks as the knowledge map, laid out on real dates. */
function Route({ model }: { model: PrepModel }) {
  const { forecast } = forecastSeries(readiness(model), model.extraDays);
  const testDate = day(11, 7);
  const { x, stops, forecastX, testX } = routeLayout(forecast, testDate);
  const inTime = forecast <= testDate;

  return (
    <div className={styles.canvasGrid}>
      <section className={`${styles.canvas} ${styles.full}`} aria-label="Маршрут">
        <header className={styles.canvasHead}>
          <h3>SAT Math · маршрут</h3>
          <span className={inTime ? styles.ok : styles.warn}>
            прогноз готовности {formatDate(forecast)} · тест {formatDate(testDate)}
          </span>
        </header>

        <div className={styles.graphScroll}>
          <div className={styles.routeMap} style={{ width: CANVAS_W, height: CANVAS_H }}>
            <svg className={styles.graphEdges} width={CANVAS_W} height={CANVAS_H} aria-hidden="true">
              {/* The line the whole route runs along */}
              <line x1={PAD - 20} y1={AXIS_Y} x2={CANVAS_W - PAD + 20} y2={AXIS_Y} className={styles.routeAxisLine} />
              {[day(9, 1), day(10, 1), day(11, 1)].map((m) => (
                <line key={m.getTime()} x1={x(m)} y1={AXIS_Y - 5} x2={x(m)} y2={AXIS_Y + 5} className={styles.routeAxisLine} />
              ))}

              {/* Today and the readiness forecast, straight down to the date line */}
              <line x1={x(TODAY)} y1={26} x2={x(TODAY)} y2={AXIS_Y} className={styles.routeNow} />
              <line x1={forecastX} y1={26} x2={forecastX} y2={AXIS_Y} className={inTime ? styles.routeOk : styles.routeLate} />
              <line x1={testX} y1={26} x2={testX} y2={AXIS_Y} className={styles.routeTestLine} />

              {stops.map((stop, i) => {
                const next = stops[i + 1];
                const to = next ? { x: next.x, y: next.y } : { x: testX, y: MID };
                const dx = to.x - stop.x;
                const dy = to.y - stop.y;
                const len = Math.hypot(dx, dy) || 1;
                const gap = SET_R + 7;
                return (
                  <line
                    key={stop.set.id}
                    x1={stop.x + (dx / len) * gap}
                    y1={stop.y + (dy / len) * gap}
                    x2={to.x - (dx / len) * (gap + (next ? 0 : 6))}
                    y2={to.y - (dy / len) * (gap + (next ? 0 : 6))}
                    className={styles.edge}
                  />
                );
              })}

              {/* Each set is tied down to its dates */}
              {stops.map((stop) => (
                <line
                  key={`drop-${stop.set.id}`}
                  x1={stop.x}
                  y1={stop.y + SET_R + 6}
                  x2={stop.x}
                  y2={AXIS_Y}
                  className={styles.routeDrop}
                />
              ))}
            </svg>

            {[day(9, 1), day(10, 1), day(11, 1)].map((m) => (
              <span key={m.getTime()} className={styles.routeMonth} style={{ left: x(m), top: AXIS_Y + 10 }}>
                {formatShort(m).replace(/^\d+ /, "")}
              </span>
            ))}

            <span className={styles.routeMark} style={{ left: x(TODAY), top: 6 }}>
              сегодня
            </span>
            <span
              className={`${styles.routeMark} ${inTime ? styles.routeMarkOk : styles.routeMarkLate}`}
              style={{ left: forecastX, top: 6 }}
            >
              прогноз
            </span>

            {stops.map((stop) => {
              const status = setStatus(model, stop.set);
              return (
                <span
                  key={stop.set.id}
                  className={styles.routeStop}
                  data-status={status}
                  style={{ left: stop.x, top: stop.y }}
                  title={`Сет ${stop.set.number} · ${stop.set.title}: ${formatShort(stop.set.start)} – ${formatShort(
                    stop.set.deadline
                  )}, ${STATUS_TEXT[status]}`}
                >
                  <SetMark status={status} />
                  <span className={`${styles.routeChip} ${stop.below ? styles.routeChipBelow : ""}`}>
                    <span className={styles.routeChipTitle}>
                      Сет {stop.set.number} · {stop.set.title}
                    </span>
                    <span className={styles.routeChipMeta}>
                      {STATUS_TEXT[status]} · до {formatShort(stop.set.deadline)}
                    </span>
                  </span>
                </span>
              );
            })}

            <span className={`${styles.routeStop} ${styles.routeExam}`} style={{ left: testX, top: MID }}>
              <span className={styles.routeExamMark} aria-hidden="true" />
              <span className={styles.routeChip}>
                <span className={styles.routeChipTitle}>Тест</span>
                <span className={styles.routeChipMeta}>{formatShort(testDate)}</span>
              </span>
            </span>
          </div>
        </div>

        <p className={styles.muted}>
          Кружок — сет на своих датах: {STATUS_TEXT.done} — залит, текущий — оранжевый, предстоит — контур, закрепление — пунктир.
        </p>
      </section>
    </div>
  );
}

/** A set drawn the same way a skill is: filled, ringed or dashed, so status is shape as well as colour. */
function SetMark({ status }: { status: keyof typeof STATUS_TEXT }) {
  const size = SET_R * 2;
  const c = SET_R;
  const r = SET_R - 2;
  const filled = status === "done" || status === "current";
  return (
    <svg className={styles.routeMarkShape} width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
      {filled ? (
        <circle cx={c} cy={c} r={r} className={styles.mapFill} />
      ) : (
        <circle
          cx={c}
          cy={c}
          r={r}
          className={`${styles.mapRing} ${status === "upcoming" ? "" : styles.mapDashed}`}
        />
      )}
    </svg>
  );
}

/* ---------- Карта навыков: the graph, and why each skill is in that state ---------- */

function KnowledgeMap({ model, onModel }: { model: PrepModel; onModel: (model: PrepModel) => void }) {
  // Nothing open at first: the card would cover the map before the student has looked at it
  const [selected, setSelected] = useState<string | null>(null);
  const current = SETS.find((s) => s.id === model.currentSet);
  const skill = selected ? skillById(selected) : null;

  return (
    <div className={styles.canvasGrid}>
      <section className={`${styles.canvas} ${styles.full}`} aria-label="Карта навыков">
        <header className={styles.canvasHead}>
          <h3>Карта навыков</h3>
          <StateLegend />
        </header>
        <SkillGraph
          states={model.states}
          recall={model.recall}
          misconceptions={model.misconceptions}
          highlight={current?.skills ?? []}
          selected={selected}
          onSelect={(id) => setSelected((s) => (s === id ? null : id))}
          onClose={() => setSelected(null)}
          details={
            skill && (
              <div className={styles.skillPanel}>
                <p className={styles.eyebrow}>{skill.area}</p>
                <h4>{skill.name}</h4>
                <p className={styles.skillState}>
                  <StateGlyph state={model.states[skill.id]} size={16} />
                  {STATE_LABEL[model.states[skill.id]]} · вспомнит сейчас ~{Math.round(model.recall[skill.id] * 100)}% · вес{" "}
                  {skill.weight}%
                </p>
                {skill.root && (
                  <p className={styles.rootNote}>
                    Корень: ошибки в «
                    {SKILLS.filter((s) => s.requires.includes(skill.id))
                      .map((s) => s.name)
                      .join(", ")}
                    » идут отсюда.
                  </p>
                )}
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
              </div>
            )
          }
        />
      </section>
    </div>
  );
}

/* ---------- Все сеты: the whole route grouped by area ---------- */

function AllSets({ model, onMakeCurrent }: { model: PrepModel; onMakeCurrent: (setId: string) => void }) {
  return (
    <div className={styles.canvasGrid}>
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
