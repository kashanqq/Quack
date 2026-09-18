"use client";

import { useState } from "react";
import { Icon } from "../choice/Icon";
import {
  AREAS,
  EXAM_IDS,
  EXAMS,
  monthStarts,
  formatDate,
  formatShort,
  forecastSeries,
  SET_STATUS_LABEL,
  SETS,
  skillById,
  SKILLS,
  STATE_LABEL,
  TODAY,
  type ExamId,
} from "./prepData";
import { closed, disputeMisconception, MISCONCEPTION_LABEL, readiness, setStatus, type PrepModel, type PrepSub } from "./prepModel";
import { useVertical } from "./GraphCanvas";
import { SkillGraph, StateGlyph, StateLegend } from "./SkillGraph";
import styles from "./prep.module.css";

type Props = {
  model: PrepModel;
  sub: PrepSub;
  /** Which exam the route, the map and the set list show */
  exam: ExamId;
  onExam: (exam: ExamId) => void;
  onMakeCurrent: (setId: string) => void;
  onModel: (model: PrepModel) => void;
};

const STATUS_TEXT = { ...SET_STATUS_LABEL, proposed: "предложен" };

/**
 * §4.3 — the route of sets and the knowledge map they are built from. Three sub-tabs: the route on a
 * timeline, the map of skills with its evidence, and the full list of sets grouped by area.
 */
export function SetsView({ model, sub, exam, onExam, onMakeCurrent, onModel }: Props) {
  const switcher = <ExamSwitch exam={exam} onExam={onExam} />;
  // Keyed by exam: the map keeps a layout and a selection per exam, and switching starts clean
  if (sub === "map") return <KnowledgeMap key={exam} exam={exam} switcher={switcher} model={model} onModel={onModel} />;
  if (sub === "all") return <AllSets exam={exam} switcher={switcher} model={model} onMakeCurrent={onMakeCurrent} />;
  return <Route exam={exam} switcher={switcher} model={model} />;
}

/** SAT Math or IELTS: each has its own route, map and sets. */
function ExamSwitch({ exam, onExam }: { exam: ExamId; onExam: (exam: ExamId) => void }) {
  return (
    <div className={styles.segmented} role="tablist" aria-label="Экзамен">
      {EXAM_IDS.map((id) => (
        <button key={id} type="button" role="tab" aria-selected={exam === id} onClick={() => onExam(id)}>
          {EXAMS[id].name}
        </button>
      ))}
    </div>
  );
}

/* ---------- Маршрут: the sets on a timeline against the test date ---------- */

const CANVAS_W = 1020;
const CANVAS_H = 286;
const PAD = 54;
const AXIS_Y = 244;
const MID = 140;
const SET_R = 22;

/** Where a set sits on the route: the middle of its window, swaying above and below the line. */
function routeLayout(exam: ExamId, forecast: Date, testDate: Date) {
  const from = EXAMS[exam].routeFrom.getTime();
  const to = EXAMS[exam].routeTo.getTime();
  const x = (d: Date) => PAD + ((d.getTime() - from) / (to - from)) * (CANVAS_W - PAD * 2);

  const stops = SETS.filter((s) => s.exam === exam).map((set, i) => ({
    set,
    x: x(new Date((set.start.getTime() + set.deadline.getTime()) / 2)),
    y: MID + (i % 2 ? 30 : -30),
    below: i % 2 === 1,
  }));

  return { x, stops, forecastX: x(forecast), testX: x(testDate) };
}

/** The route as a chain of circles: the same marks as the knowledge map, laid out on real dates. */
function Route({ exam, switcher, model }: { exam: ExamId; switcher: React.ReactNode; model: PrepModel }) {
  const { forecast } = forecastSeries(readiness(model, exam), model.extraDays, exam);
  const testDate = EXAMS[exam].test;
  const { x, stops, forecastX, testX } = routeLayout(exam, forecast, testDate);
  const months = monthStarts(EXAMS[exam].routeFrom, EXAMS[exam].routeTo);
  const inTime = forecast <= testDate;
  const vertical = useVertical();

  return (
    <div className={styles.canvasGrid}>
      <section className={`${styles.canvas} ${styles.full}`} aria-label="Маршрут">
        <header className={styles.canvasHead}>
          <h3>{EXAMS[exam].name} · маршрут</h3>
          {switcher}
          <span className={inTime ? styles.ok : styles.warn}>
            прогноз готовности {formatDate(forecast)} · тест {formatDate(testDate)}
          </span>
        </header>

        {vertical ? (
          <RouteColumn exam={exam} model={model} forecast={forecast} testDate={testDate} inTime={inTime} />
        ) : (
          <div className={styles.graphScroll}>
            <div className={styles.routeMap} style={{ width: CANVAS_W, height: CANVAS_H }}>
              <svg className={styles.graphEdges} width={CANVAS_W} height={CANVAS_H} aria-hidden="true">
                {/* The line the whole route runs along */}
                <line x1={PAD - 20} y1={AXIS_Y} x2={CANVAS_W - PAD + 20} y2={AXIS_Y} className={styles.routeAxisLine} />
                {months.map((m) => (
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

              {months.map((m) => (
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
                        {isNow(status) && <b className={styles.routeNowTag}>сейчас</b>}
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
        )}

        <p className={styles.muted}>
          Кружок — сет на своих датах: {STATUS_TEXT.done} — залит, текущий — оранжевый и пульсирует, предстоит — контур, закрепление — пунктир.
        </p>
      </section>
    </div>
  );
}

/* On a phone the route runs down the screen: dates go down an axis on the left, each set sits at the
   middle of its window with its label to the right, today and the forecast are marked in the margin. */

const V_AXIS_X = 84;
const V_TOP = 26;
const V_BOTTOM = 40;
const DAY_MS = 86_400_000;
/**
 * The column is not to scale: neighbouring marks sit at least V_MIN_GAP apart, so labels of up to two
 * lines never touch, and at most V_MAX_GAP, so a long quiet stretch does not turn into a long empty
 * axis to scroll past. Dates in between (months, today, the forecast) are placed between their neighbours.
 */
const V_MIN_GAP = 64;
const V_MAX_GAP = 92;
const V_PER_DAY = 5;

const clampGap = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

function columnScale(marks: number[], from: number, to: number) {
  const anchors: [number, number][] = [[from, V_TOP]];
  for (const t of marks) {
    const [pt, py] = anchors[anchors.length - 1];
    // The first set only needs room for the month label above it
    const lo = anchors.length === 1 ? 44 : V_MIN_GAP;
    anchors.push([t, py + clampGap(((t - pt) / DAY_MS) * V_PER_DAY, lo, V_MAX_GAP)]);
  }
  const [lt, ly] = anchors[anchors.length - 1];
  anchors.push([to, ly + clampGap(((to - lt) / DAY_MS) * V_PER_DAY, 20, 40)]);

  return (d: Date | number) => {
    const t = +d;
    let i = anchors.findIndex(([at]) => at >= t);
    if (i <= 0) i = i === 0 ? 1 : anchors.length - 1;
    const [t0, y0] = anchors[i - 1];
    const [t1, y1] = anchors[i];
    return y0 + ((t - t0) / (t1 - t0 || 1)) * (y1 - y0);
  };
}

function RouteColumn({
  exam,
  model,
  forecast,
  testDate,
  inTime,
}: {
  exam: ExamId;
  model: PrepModel;
  forecast: Date;
  testDate: Date;
  inTime: boolean;
}) {
  const from = EXAMS[exam].routeFrom.getTime();
  const to = EXAMS[exam].routeTo.getTime();
  const stops = SETS.filter((s) => s.exam === exam).map((set) => ({ set, at: (set.start.getTime() + set.deadline.getTime()) / 2 }));

  const marks = [...stops.map((stop) => stop.at), testDate.getTime()].sort((a, b) => a - b);
  const y = columnScale(marks, from, to);
  const height = Math.max(y(to), y(forecast) + 16) + V_BOTTOM;
  const months = monthStarts(EXAMS[exam].routeFrom, EXAMS[exam].routeTo);

  return (
    <div className={`${styles.routeMap} ${styles.routeColumn}`} style={{ height, ["--axis-x" as string]: `${V_AXIS_X}px` }}>
      <svg className={styles.graphEdges} width="100%" height={height} aria-hidden="true">
        <line x1={V_AXIS_X} y1={V_TOP - 14} x2={V_AXIS_X} y2={height - 16} className={styles.routeAxisLine} />
        {months.map((m) => (
          <line key={m.getTime()} x1={V_AXIS_X - 5} y1={y(m)} x2={V_AXIS_X + 5} y2={y(m)} className={styles.routeAxisLine} />
        ))}
        <line x1={V_AXIS_X - 10} y1={y(TODAY)} x2={V_AXIS_X + 18} y2={y(TODAY)} className={styles.routeNow} />
        <line x1={V_AXIS_X - 10} y1={y(forecast)} x2={V_AXIS_X + 18} y2={y(forecast)} className={inTime ? styles.routeOk : styles.routeLate} />
      </svg>

      {months.map((m) => (
        <span key={m.getTime()} className={`${styles.routeMonth} ${styles.routeSideLabel}`} style={{ top: y(m) }}>
          {formatShort(m).replace(/^\d+ /, "")}
        </span>
      ))}
      <span className={`${styles.routeMark} ${styles.routeSideLabel}`} style={{ top: y(TODAY) }}>
        сегодня
      </span>
      <span
        className={`${styles.routeMark} ${styles.routeSideLabel} ${inTime ? styles.routeMarkOk : styles.routeMarkLate}`}
        style={{ top: y(forecast) }}
      >
        прогноз
      </span>

      {stops.map(({ set, at }) => {
        const status = setStatus(model, set);
        return (
          <div
            key={set.id}
            className={`${styles.routeStop} ${styles.routeRow}`}
            data-status={status}
            style={{ top: y(at) }}
            title={`Сет ${set.number} · ${set.title}: ${formatShort(set.start)} – ${formatShort(set.deadline)}, ${STATUS_TEXT[status]}`}
          >
            <span className={styles.routeAnchor}>
              <SetMark status={status} />
            </span>
            <span className={`${styles.routeChip} ${styles.routeChipSide}`}>
              <span className={styles.routeChipTitle}>
                Сет {set.number} · {set.title}
              </span>
              <span className={styles.routeChipMeta}>
                {isNow(status) && <b className={styles.routeNowTag}>сейчас</b>}
                {STATUS_TEXT[status]} · до {formatShort(set.deadline)}
              </span>
            </span>
          </div>
        );
      })}

      <div className={`${styles.routeStop} ${styles.routeExam} ${styles.routeRow}`} style={{ top: y(testDate) }}>
        <span className={styles.routeAnchor}>
          <span className={styles.routeExamMark} aria-hidden="true" />
        </span>
        <span className={`${styles.routeChip} ${styles.routeChipSide}`}>
          <span className={styles.routeChipTitle}>Тест</span>
          <span className={styles.routeChipMeta}>{formatShort(testDate)}</span>
        </span>
      </div>
    </div>
  );
}

/** The set the student is on: the one in work, or the one waiting to be accepted when none is. */
const isNow = (status: keyof typeof STATUS_TEXT) => status === "current" || status === "proposed";

/**
 * A set drawn the same way a skill is: filled, ringed or dashed, so status is shape as well as colour.
 * The set the student is on sends out a slow ring, so «где я сейчас» is found at a glance.
 */
function SetMark({ status }: { status: keyof typeof STATUS_TEXT }) {
  const size = SET_R * 2;
  const c = SET_R;
  const r = SET_R - 2;
  const filled = status === "done" || status === "current";
  return (
    <svg className={styles.routeMarkShape} width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
      {isNow(status) && (
        <>
          <circle cx={c} cy={c} r={r} className={styles.routePulse} />
          <circle cx={c} cy={c} r={r} className={`${styles.routePulse} ${styles.routePulseLate}`} />
        </>
      )}
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

function KnowledgeMap({
  exam,
  switcher,
  model,
  onModel,
}: {
  exam: ExamId;
  switcher: React.ReactNode;
  model: PrepModel;
  onModel: (model: PrepModel) => void;
}) {
  // Nothing open at first: the card would cover the map before the student has looked at it
  const [selected, setSelected] = useState<string | null>(null);
  const current = SETS.find((s) => s.id === model.currentSet);
  const skill = selected ? skillById(selected) : null;

  return (
    <div className={styles.canvasGrid}>
      <section className={`${styles.canvas} ${styles.full}`} aria-label="Карта навыков">
        <header className={styles.canvasHead}>
          <h3>Карта навыков · {EXAMS[exam].name}</h3>
          {switcher}
          <StateLegend />
        </header>
        <SkillGraph
          exam={exam}
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

function AllSets({
  exam,
  switcher,
  model,
  onMakeCurrent,
}: {
  exam: ExamId;
  switcher: React.ReactNode;
  model: PrepModel;
  onMakeCurrent: (setId: string) => void;
}) {
  return (
    <div className={styles.canvasGrid}>
      <section className={`${styles.canvas} ${styles.full}`} aria-label="Все сеты">
        <header className={styles.canvasHead}>
          <h3>Все сеты · {EXAMS[exam].name}</h3>
          {switcher}
          <span className={styles.muted}>текущий можно сменить — прогноз пересчитается</span>
        </header>
        <div className={styles.areaGroups}>
          {AREAS[exam].map((area) => {
            const sets = SETS.filter((s) => s.exam === exam && s.area === area);
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
