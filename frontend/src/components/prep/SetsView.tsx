"use client";

import { useLayoutEffect, useRef, useState } from "react";
import { Icon } from "../choice/Icon";
import {
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
import { closed, disputeMisconception, MISCONCEPTION_LABEL, rankSets, readiness, setStatus, type PrepModel, type PrepSub } from "./prepModel";
import { SetDetail } from "./SetDetail";
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
  /** The set opened from the list (or from «Обзор»), with the topic to show first */
  openSet: { id: string; topic?: string } | null;
  onOpenSet: (setId: string | null, topic?: string) => void;
  onToast: (text: string) => void;
};

const STATUS_TEXT = { ...SET_STATUS_LABEL, proposed: "предложен" };

/**
 * §4.3 — the route of sets and the knowledge map they are built from. Three sub-tabs: the route on a
 * timeline, the map of skills with its evidence, and the full list of sets grouped by area.
 */
export function SetsView({ model, sub, exam, onExam, onMakeCurrent, onModel, openSet, onOpenSet, onToast }: Props) {
  const switcher = <ExamSwitch exam={exam} onExam={onExam} />;
  // Keyed by exam: the map keeps a layout and a selection per exam, and switching starts clean
  if (sub === "map") return <KnowledgeMap key={exam} exam={exam} switcher={switcher} model={model} onModel={onModel} onOpen={(id, topic) => onOpenSet(id, topic)} />;
  if (sub === "route") return <Route exam={exam} switcher={switcher} model={model} onOpen={(id) => onOpenSet(id)} />;
  const set = openSet ? SETS.find((s) => s.id === openSet.id) : undefined;
  if (set) {
    return (
      <SetDetail
        key={set.id}
        model={model}
        set={set}
        topic={openSet?.topic}
        onBack={() => onOpenSet(null)}
        onMakeCurrent={onMakeCurrent}
        onModel={onModel}
        onToast={onToast}
      />
    );
  }
  return <SetList exam={exam} switcher={switcher} model={model} onOpen={(id) => onOpenSet(id)} />;
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

/** The least the route needs; on a big screen it grows to the whole card */
const MIN_W = 1020;
const MIN_H = 286;
const PAD = 54;
const SET_R = 22;

/** Where a set sits on the route: the middle of its window, swaying above and below the line. */
function routeLayout(exam: ExamId, forecast: Date, testDate: Date, width: number, height: number) {
  const from = EXAMS[exam].routeFrom.getTime();
  const to = EXAMS[exam].routeTo.getTime();
  const x = (d: Date) => PAD + ((d.getTime() - from) / (to - from)) * (width - PAD * 2);
  const axisY = height - 42;
  // Sets hang in the middle of the room above the axis; the taller it is, the wider they sway
  const mid = 26 + (axisY - 26) / 2 + 12;
  const sway = Math.min(110, 30 + (height - MIN_H) * 0.2);

  const stops = SETS.filter((s) => s.exam === exam).map((set, i) => ({
    set,
    x: x(new Date((set.start.getTime() + set.deadline.getTime()) / 2)),
    y: mid + (i % 2 ? sway : -sway),
    below: i % 2 === 1,
  }));

  return { x, stops, forecastX: x(forecast), testX: x(testDate), axisY, mid };
}

/** The size of a box the drawing should fill */
function useBoxSize() {
  const ref = useRef<HTMLDivElement>(null);
  const [box, setBox] = useState({ w: MIN_W, h: MIN_H });
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const measure = () => setBox({ w: el.clientWidth, h: el.clientHeight });
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  return [ref, box] as const;
}

/** The route as a chain of circles: the same marks as the knowledge map, laid out on real dates. */
function Route({
  exam,
  switcher,
  model,
  onOpen,
}: {
  exam: ExamId;
  switcher: React.ReactNode;
  model: PrepModel;
  onOpen: (setId: string) => void;
}) {
  const { forecast } = forecastSeries(readiness(model, exam), model.extraDays, exam);
  const testDate = EXAMS[exam].test;
  const [boxRef, box] = useBoxSize();
  // The scroll box has a little padding and maybe a scrollbar: stay inside it, never push it to grow
  const width = Math.max(MIN_W, box.w);
  const height = Math.max(MIN_H, box.h - 12);
  const { x, stops, forecastX, testX, axisY: AXIS_Y, mid: MID } = routeLayout(exam, forecast, testDate, width, height);
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
          <RouteColumn exam={exam} model={model} forecast={forecast} testDate={testDate} inTime={inTime} onOpen={onOpen} />
        ) : (
          <div className={`${styles.graphScroll} ${styles.routeScroll}`} ref={boxRef}>
            <div className={styles.routeMap} style={{ width, height }}>
              <svg className={styles.graphEdges} width={width} height={height} aria-hidden="true">
                {/* The line the whole route runs along */}
                <line x1={PAD - 20} y1={AXIS_Y} x2={width - PAD + 20} y2={AXIS_Y} className={styles.routeAxisLine} />
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
                  <button
                    type="button"
                    key={stop.set.id}
                    className={`${styles.routeStop} ${styles.routeStopOpen}`}
                    data-status={status}
                    style={{ left: stop.x, top: stop.y }}
                    title={`Открыть сет ${stop.set.number} · ${stop.set.title}: ${formatShort(stop.set.start)} – ${formatShort(
                      stop.set.deadline
                    )}, ${STATUS_TEXT[status]}`}
                    onClick={() => onOpen(stop.set.id)}
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
                  </button>
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
          Нажми на сет, чтобы открыть его. Кружок — сет на своих датах: {STATUS_TEXT.done} — залит, текущий — оранжевый и пульсирует, предстоит — контур, закрепление — пунктир.
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
  onOpen,
}: {
  exam: ExamId;
  model: PrepModel;
  forecast: Date;
  testDate: Date;
  inTime: boolean;
  onOpen: (setId: string) => void;
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
          <button
            type="button"
            key={set.id}
            className={`${styles.routeStop} ${styles.routeRow} ${styles.routeStopOpen}`}
            data-status={status}
            style={{ top: y(at) }}
            title={`Открыть сет ${set.number} · ${set.title}: ${formatShort(set.start)} – ${formatShort(set.deadline)}, ${STATUS_TEXT[status]}`}
            onClick={() => onOpen(set.id)}
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
          </button>
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
  onOpen,
}: {
  exam: ExamId;
  switcher: React.ReactNode;
  model: PrepModel;
  onModel: (model: PrepModel) => void;
  /** Into the set's graph, with this skill's topic open first */
  onOpen: (setId: string, topic: string) => void;
}) {
  // Nothing open at first: the card would cover the map before the student has looked at it
  const [selected, setSelected] = useState<string | null>(null);
  const current = SETS.find((s) => s.id === model.currentSet);
  const skill = selected ? skillById(selected) : null;
  // Where the title leads: the first set with this skill that is still ahead, else the last one passed
  const target = skill
    ? (SETS.find((s) => s.skills.includes(skill.id) && !model.doneSets.includes(s.id)) ?? SETS.find((s) => s.skills.includes(skill.id)))
    : undefined;

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
                {target ? (
                  <h4>
                    <button
                      type="button"
                      className={styles.skillTitleLink}
                      title={`Открыть сет ${target.number} · ${target.title} на этой теме`}
                      onClick={() => onOpen(target.id, skill.id)}
                    >
                      {skill.name}
                      <Icon name="chevron-right" size={16} />
                    </button>
                  </h4>
                ) : (
                  <h4>{skill.name}</h4>
                )}
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

/* ---------- Сеты: three recommended first, then the rest ---------- */

const RECOMMENDED = 3;

function SetList({
  exam,
  switcher,
  model,
  onOpen,
}: {
  exam: ExamId;
  switcher: React.ReactNode;
  model: PrepModel;
  onOpen: (setId: string) => void;
}) {
  const ranked = rankSets(model, exam);
  const top = ranked.slice(0, RECOMMENDED);
  const topIds = new Set(top.map((r) => r.set.id));
  // The rest keep the route's order, so they read as the plan they are part of
  const rest = SETS.filter((s) => s.exam === exam && !topIds.has(s.id) && !model.doneSets.includes(s.id));
  const done = SETS.filter((s) => s.exam === exam && model.doneSets.includes(s.id));

  return (
    <div className={styles.setList}>
      <header className={styles.setListHead}>
        <div>
          <h3>Рекомендуем сейчас</h3>
          <p className={styles.muted}>по твоим ошибкам и темам, которые ещё не держатся</p>
        </div>
        {switcher}
      </header>

      {top.length ? (
        <div className={styles.recGrid}>
          {top.map(({ set, reasons }, i) => (
            <SetCard key={set.id} model={model} set={set} rank={i + 1} reasons={reasons} onOpen={onOpen} />
          ))}
        </div>
      ) : (
        <p className={styles.muted}>Все сеты по {EXAMS[exam].name} пройдены — осталось закрепление и тест.</p>
      )}

      {rest.length > 0 && (
        <>
          <p className={styles.eyebrow}>Остальные сеты</p>
          <div className={styles.setGridSmall}>
            {rest.map((set) => (
              <SetCard key={set.id} model={model} set={set} onOpen={onOpen} />
            ))}
          </div>
        </>
      )}

      {done.length > 0 && (
        <>
          <p className={styles.eyebrow}>Пройденные</p>
          <div className={styles.setGridSmall}>
            {done.map((set) => (
              <SetCard key={set.id} model={model} set={set} onOpen={onOpen} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function SetCard({
  model,
  set,
  rank,
  reasons,
  onOpen,
}: {
  model: PrepModel;
  set: (typeof SETS)[number];
  /** Place among the recommended; absent for the rest */
  rank?: number;
  reasons?: string[];
  onOpen: (setId: string) => void;
}) {
  const status = setStatus(model, set);
  const left = Math.round((set.deadline.getTime() - TODAY.getTime()) / 86_400_000);
  return (
    <article
      className={`${styles.setCard} ${rank ? styles.setCardRec : ""}`}
      data-status={status}
      onClick={() => onOpen(set.id)}
    >
      <div className={styles.setHead}>
        <span className={styles.setCardTitle}>
          {rank && <b className={styles.recRank}>{rank}</b>}
          <strong>
            Сет {set.number} · {set.title}
          </strong>
        </span>
        <span className={styles.statusPill} data-status={status}>
          {STATUS_TEXT[status]}
        </span>
      </div>
      <span className={styles.muted}>
        {formatShort(set.start)} – {formatShort(set.deadline)}
        {status !== "done" && left >= 0 && ` · осталось ${left} дн.`} · доказано {closed(model, set)} из {set.skills.length}
      </span>
      <ul className={styles.skillChips}>
        {set.skills.map((id) => (
          <li key={id}>
            <StateGlyph state={model.states[id]} size={12} />
            {skillById(id).name}
          </li>
        ))}
      </ul>
      {reasons ? (
        <ul className={styles.recReasons}>
          {reasons.slice(0, 3).map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      ) : (
        <p className={styles.why}>{set.why}</p>
      )}
      <button
        type="button"
        className={rank ? styles.primary : styles.secondary}
        onClick={(e) => {
          e.stopPropagation();
          onOpen(set.id);
        }}
      >
        Открыть сет <Icon name="chevron-right" size={16} />
      </button>
    </article>
  );
}
