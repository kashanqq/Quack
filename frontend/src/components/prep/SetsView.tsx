"use client";

import { useLayoutEffect, useRef, useState } from "react";
import { Icon } from "../choice/Icon";
import {
  EXAM_IDS,
  EXAMS,
  formatDate,
  formatShort,
  SET_STATUS_LABEL,
  SETS,
  skillById,
  SKILLS,
  STATE_LABEL,
  type ExamId,
  type StudySet,
} from "./prepData";
import {
  closed,
  disputeMisconception,
  MISCONCEPTION_LABEL,
  setStatus,
  type PrepModel,
  type PrepSub,
} from "./prepModel";
import { SetDetail } from "./SetDetail";
import { RouteView } from "./RouteView";
import { useVertical } from "./GraphCanvas";
import { SkillGraph, StateGlyph, StateLegend } from "./SkillGraph";
import { TOPICS } from "./topicContent";
import styles from "./prep.module.css";

type Props = {
  model: PrepModel;
  sub: PrepSub;
  /** Which exam the sets and the map show */
  exam: ExamId;
  onExam: (exam: ExamId) => void;
  /** Takes a set into work, replacing the one in work */
  onMakeCurrent: (setId: string) => void;
  onModel: (model: PrepModel) => void;
  /** The set opened from the route (or from «Обзор»), with the topic to show first */
  openSet: { id: string; topic?: string } | null;
  onOpenSet: (setId: string | null, topic?: string) => void;
  onToast: (text: string) => void;
  onOpenDiagnostic?: () => void;
};

const STATUS_TEXT = { ...SET_STATUS_LABEL, proposed: "предложен" };

/**
 * §4.3 — sets. «Маршрут» holds the sets the assistant built for the student, in order; the student works
 * on one and can swap it for another at any time. «Карта навыков» shows the same sets as an interactive map
 * with toggle between Set Map and full Skill Graph.
 */
export function SetsView({ model, sub, exam, onExam, onMakeCurrent, onModel, openSet, onOpenSet, onToast, onOpenDiagnostic }: Props) {
  const switcher = <ExamSwitch exam={exam} onExam={onExam} />;
  const [mapMode, setMapMode] = useState<"sets" | "skills">("sets");
  const [selectedSkill, setSelectedSkill] = useState<string | null>(null);

  if (sub === "map") {
    return (
      <div className={styles.canvasGrid}>
        <section className={`${styles.canvas} ${styles.full} ${styles.setMapCard}`} aria-label="Карта навыков">
          <header className={styles.canvasHead}>
            <div className={styles.canvasTitleRow}>
              <h3>Карта навыков · {EXAMS[exam].name}</h3>
              <div className={styles.mapModeSwitch} role="tablist" aria-label="Режим отображения карты">
                <button
                  type="button"
                  role="tab"
                  aria-selected={mapMode === "sets"}
                  onClick={() => setMapMode("sets")}
                >
                  По сетам
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={mapMode === "skills"}
                  onClick={() => setMapMode("skills")}
                >
                  Граф знаний
                </button>
              </div>
            </div>

            <div className={styles.canvasControlsRight}>
              {switcher}
              <StateLegend />
            </div>
          </header>

          {mapMode === "sets" ? (
            <SetMap
              key={exam}
              exam={exam}
              model={model}
              onModel={onModel}
              onOpen={(id, topic) => onOpenSet(id, topic)}
              onTake={onMakeCurrent}
            />
          ) : (
            <div className={styles.skillGraphWrapper}>
              <SkillGraph
                key={`${exam}-skills`}
                exam={exam}
                states={model.states}
                recall={model.recall}
                misconceptions={model.misconceptions}
                highlight={SETS.find((s) => s.id === model.currentSet)?.skills ?? []}
                selected={selectedSkill}
                onSelect={(id) => setSelectedSkill(id === selectedSkill ? null : id)}
                details={
                  selectedSkill ? (
                    <SkillDetails
                      model={model}
                      skillId={selectedSkill}
                      onModel={onModel}
                      onOpen={() => {
                        const s = SETS.find((set) => set.skills.includes(selectedSkill) && set.exam === exam);
                        if (s) onOpenSet(s.id, selectedSkill);
                      }}
                    />
                  ) : undefined
                }
                onClose={() => setSelectedSkill(null)}
              />
            </div>
          )}
        </section>
      </div>
    );
  }

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

  return (
    <RouteView
      exam={exam}
      switcher={switcher}
      model={model}
      onOpen={(id, topic) => onOpenSet(id, topic)}
      onTake={onMakeCurrent}
      onOpenDiagnostic={onOpenDiagnostic}
    />
  );
}

/** SAT Math or ЕНТ: each has its own sets and map. */
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

/** Topic states of a set as a row of small bars */
function Segments({ model, set }: { model: PrepModel; set: StudySet }) {
  return (
    <span className={styles.segments}>
      {set.skills.map((id) => (
        <span key={id} data-state={model.states[id]} title={`${skillById(id).name}: ${STATE_LABEL[model.states[id]]}`} />
      ))}
    </span>
  );
}

/* ---------- Карта навыков: the sets as a map, each with its topics inside ---------- */

/**
 * Set B rests on set A when a topic of B needs a topic of A. A review set rests on the sets whose topics
 * it goes over.
 */
function rests(b: StudySet, a: StudySet): boolean {
  return (
    a.id !== b.id &&
    a.status !== "review" &&
    (b.skills.some((id) => skillById(id).requires.some((r) => a.skills.includes(r))) ||
      (b.status === "review" && b.skills.some((id) => a.skills.includes(id))))
  );
}

function setLinks(exam: ExamId) {
  const sets = SETS.filter((s) => s.exam === exam);
  const before = Object.fromEntries(sets.map((b) => [b.id, sets.filter((a) => rests(b, a)).map((a) => a.id)]));
  const depth: Record<string, number> = {};
  const depthOf = (id: string, seen: string[] = []): number => {
    if (id in depth) return depth[id];
    const prev = before[id].filter((p) => !seen.includes(p));
    return (depth[id] = prev.length ? 1 + Math.max(...prev.map((p) => depthOf(p, [...seen, id]))) : 0);
  };
  sets.forEach((s) => depthOf(s.id));
  const columns: StudySet[][] = [];
  sets.forEach((s) => (columns[depth[s.id]] ??= []).push(s));
  const edges = sets.flatMap((b) => before[b.id].map((a) => ({ from: a, to: b.id })));
  return { columns: columns.filter(Boolean), edges, before };
}

function SetMap({
  exam,
  model,
  onModel,
  onOpen,
  onTake,
}: {
  exam: ExamId;
  model: PrepModel;
  onModel: (model: PrepModel) => void;
  onOpen: (setId: string, topic?: string) => void;
  onTake: (setId: string) => void;
}) {
  const vertical = useVertical();
  const sets = SETS.filter((s) => s.exam === exam);
  const { columns, edges } = setLinks(exam);
  // The set in work is where the student looks first
  const [selected, setSelected] = useState<string | null>(() =>
    SETS.some((s) => s.id === model.currentSet && s.exam === exam) ? model.currentSet : null
  );
  const [topic, setTopic] = useState<string | null>(null);
  const set = SETS.find((s) => s.id === selected);

  // Links are drawn between the cards where they actually are
  const boxRef = useRef<HTMLDivElement>(null);
  const cardRefs = useRef<Record<string, HTMLElement | null>>({});
  const [boxes, setBoxes] = useState<Record<string, { x: number; y: number; w: number; h: number }>>({});
  const [size, setSize] = useState({ w: 0, h: 0 });
  useLayoutEffect(() => {
    const box = boxRef.current;
    if (!box) return;
    const measure = () => {
      const next: typeof boxes = {};
      for (const [id, el] of Object.entries(cardRefs.current)) {
        if (el) next[id] = { x: el.offsetLeft, y: el.offsetTop, w: el.offsetWidth, h: el.offsetHeight };
      }
      setBoxes(next);
      const all = Object.values(next);
      setSize({ w: Math.max(0, ...all.map((b) => b.x + b.w)), h: Math.max(0, ...all.map((b) => b.y + b.h)) });
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(box);
    return () => observer.disconnect();
  }, [vertical, exam, selected]);

  // Roots and confirmed traps are one dot on the card; the panel names them
  const flags = (s: StudySet) =>
    s.skills
      .flatMap((id) => [
        skillById(id).root && model.states[id] !== "solid" ? `корень: ${skillById(id).name}` : "",
        model.misconceptions[id].some((m) => m.status === "confirmed") ? `ловушка: ${skillById(id).name}` : "",
      ])
      .filter(Boolean)
      .join(", ");

  const related = new Set(selected ? edges.filter((e) => e.from === selected || e.to === selected).flatMap((e) => [e.from, e.to]) : []);

  // What this set rests on, and what it unlocks
  const dependsOn = set ? sets.filter((a) => rests(set, a)) : [];
  const unlocks = set ? sets.filter((b) => rests(b, set)) : [];

  const path = (from: string, to: string) => {
    const a = boxes[from];
    const b = boxes[to];
    if (!a || !b) return "";
    if (vertical) {
      const [x1, y1, x2, y2] = [a.x + a.w / 2, a.y + a.h, b.x + b.w / 2, b.y];
      const r = Math.max(24, (y2 - y1) / 2);
      return `M${x1},${y1} C${x1},${y1 + r} ${x2},${y2 - r} ${x2},${y2}`;
    }
    const [x1, y1, x2, y2] = [a.x + a.w, a.y + a.h / 2, b.x, b.y + b.h / 2];
    const r = Math.max(30, (x2 - x1) / 2);
    return `M${x1},${y1} C${x1 + r},${y1} ${x2 - r},${y2} ${x2},${y2}`;
  };

  return (
    <div className={styles.setMapBody} data-panel={set ? "" : undefined}>
      <div className={styles.setMapScroll} ref={boxRef} onClick={(e) => e.target === e.currentTarget && setSelected(null)}>
        <svg className={styles.graphEdges} width={size.w} height={size.h} aria-hidden="true">
          {edges.map((e) => (
            <path
              key={`${e.from}-${e.to}`}
              d={path(e.from, e.to)}
              className={styles.edge}
              data-active={selected && (e.from === selected || e.to === selected) ? "" : undefined}
            />
          ))}
        </svg>
        {columns.map((column, c) => (
          <div key={c} className={styles.setMapColumn}>
            {column.map((s) => {
              const status = setStatus(model, s);
              const isCurrent = model.currentSet === s.id;
              return (
                <button
                  key={s.id}
                  ref={(el) => {
                    cardRefs.current[s.id] = el;
                  }}
                  type="button"
                  className={styles.setMapNode}
                  aria-label={`Сет ${s.number} · ${s.title}, ${STATUS_TEXT[status]}`}
                  data-status={status}
                  data-current={isCurrent || undefined}
                  data-selected={selected === s.id || undefined}
                  data-dim={selected && selected !== s.id && !related.has(s.id) ? "" : undefined}
                  onClick={() => {
                    setSelected(s.id === selected ? null : s.id);
                    setTopic(null);
                  }}
                >
                  <span className={styles.setMapNodeHead}>
                    <strong>Сет {s.number}</strong>
                    {isCurrent && <span className={styles.activeNodePill}>В работе</span>}
                    {flags(s) && <span className={styles.setMapFlag} title={flags(s)} />}
                    <span className={styles.setMapDot} data-status={status} title={STATUS_TEXT[status]} />
                  </span>
                  <span className={styles.setMapNodeTitle}>{s.title}</span>
                  <Segments model={model} set={s} />
                </button>
              );
            })}
          </div>
        ))}
      </div>

      {set && (
        <aside className={styles.setMapPanel} aria-label={`Сет ${set.number}`}>
          <header className={styles.setMapPanelHead}>
            <div>
              <p className={styles.eyebrow}>
                Сет {set.number} · {set.area}
              </p>
              <button
                type="button"
                className={styles.setMapTitleBtn}
                onClick={() => onOpen(set.id)}
                title="Открыть этот сет"
                aria-label={`Открыть сет ${set.number}: ${set.title}`}
              >
                <h4>{set.title}</h4>
                <Icon name="chevron-right" size={15} className={styles.setMapTitleIcon} />
              </button>
            </div>
            <button type="button" className={styles.topicClose} aria-label="Закрыть панель" onClick={() => setSelected(null)}>
              <Icon name="x" size={15} />
            </button>
          </header>

          <p className={styles.muted}>
            {formatDate(set.deadline)} · доказано {closed(model, set)} из {set.skills.length}
          </p>

          {/* Action buttons: 1 Active Set switch */}
          <div className={styles.actions}>
            {model.currentSet === set.id ? (
              <span className={styles.currentActivePill}>
                <Icon name="check" size={14} /> Выбран активным
              </span>
            ) : (
              <button type="button" className={styles.secondary} onClick={() => onTake(set.id)}>
                <Icon name="check" size={14} /> Сделать активным
              </button>
            )}
          </div>

          {/* Dependencies / Unlocks badges */}
          {(dependsOn.length > 0 || unlocks.length > 0) && (
            <div className={styles.setMapDependencies}>
              {dependsOn.length > 0 && (
                <div className={styles.dependencyItem}>
                  <span className={styles.dependencyLabel}>Опирается на:</span>
                  <span className={styles.dependencySets}>
                    {dependsOn.map((d) => (
                      <button
                        key={d.id}
                        type="button"
                        className={styles.dependencyChip}
                        onClick={() => setSelected(d.id)}
                      >
                        Сет {d.number}
                      </button>
                    ))}
                  </span>
                </div>
              )}
              {unlocks.length > 0 && (
                <div className={styles.dependencyItem}>
                  <span className={styles.dependencyLabel}>Открывает:</span>
                  <span className={styles.dependencySets}>
                    {unlocks.map((u) => (
                      <button
                        key={u.id}
                        type="button"
                        className={styles.dependencyChip}
                        onClick={() => setSelected(u.id)}
                      >
                        Сет {u.number}
                      </button>
                    ))}
                  </span>
                </div>
              )}
            </div>
          )}

          <p className={styles.eyebrow}>Темы сета</p>
          <ul className={styles.setMapTopicList}>
            {set.skills.map((id) => (
              <li key={id}>
                <button type="button" aria-expanded={topic === id} onClick={() => setTopic(topic === id ? null : id)}>
                  <StateGlyph state={model.states[id]} size={12} />
                  <span>
                    {skillById(id).name}
                    {skillById(id).root && <b className={styles.rootTag}>корень</b>}
                    {model.misconceptions[id].some((m) => m.status === "confirmed") && <b className={styles.trapTag}>ловушка</b>}
                  </span>
                  <span className={styles.muted}>{STATE_LABEL[model.states[id]]}</span>
                </button>
                {topic === id && <SkillDetails model={model} skillId={id} onModel={onModel} onOpen={() => onOpen(set.id, id)} />}
              </li>
            ))}
          </ul>
        </aside>
      )}
    </div>
  );
}

/** Why a topic is in its state: summary, traps, where it leads, and the evidence behind it */
function SkillDetails({
  model,
  skillId,
  onModel,
  onOpen,
}: {
  model: PrepModel;
  skillId: string;
  onModel: (model: PrepModel) => void;
  onOpen: () => void;
}) {
  const skill = skillById(skillId);
  const topicInfo = TOPICS[skillId];
  const needs = SKILLS.filter((s) => s.requires.includes(skill.id));
  return (
    <div className={styles.skillPanel}>
      <p className={styles.skillState}>{STATE_LABEL[model.states[skill.id]]}</p>

      {/* Brief topic summary */}
      {topicInfo?.summary && (
        <p className={styles.skillSummaryText}>{topicInfo.summary}</p>
      )}

      {/* Common trap hint */}
      {topicInfo?.trap && (
        <div className={styles.skillTrapHint}>
          <Icon name="triangle-alert" size={13} />
          <span>Типичная ошибка: {topicInfo.trap}</span>
        </div>
      )}

      {skill.root && needs.length > 0 && (
        <p className={styles.rootNote}>Корень: ошибки в «{needs.map((s) => s.name).join(", ")}» идут отсюда.</p>
      )}

      <dl className={styles.facts}>
        <div>
          <dt>Опирается на</dt>
          <dd>{skill.requires.map((id) => skillById(id).name).join(", ") || "—"}</dd>
        </div>
        <div>
          <dt>Нужен для</dt>
          <dd>{needs.map((s) => s.name).join(", ") || "—"}</dd>
        </div>
      </dl>

      {model.misconceptions[skill.id].length > 0 && (
        <ul className={styles.plainList}>
          {model.misconceptions[skill.id].map((m) => (
            <li key={m.id} className={styles.misconception} data-status={m.status}>
              <span>{m.text}</span>
              <span className={styles.muted}>{MISCONCEPTION_LABEL(m)}</span>
              {(m.status === "confirmed" || m.status === "suspected") && (
                <button type="button" className={styles.link} onClick={() => onModel(disputeMisconception(model, skill.id, m.id))}>
                  Не согласен
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {model.evidence[skill.id].length > 0 && (
        <ul className={styles.evidence}>
          {model.evidence[skill.id].slice(0, 3).map((e, i) => (
            <li key={i}>
              <span className={styles.sourceTag}>{e.source}</span>
              <span>{e.text}</span>
              <span className={styles.muted}>{formatShort(e.date)}</span>
            </li>
          ))}
        </ul>
      )}
      <button type="button" className={styles.link} onClick={onOpen}>
        Открыть тему в сете →
      </button>
    </div>
  );
}
