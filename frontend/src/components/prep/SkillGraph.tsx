"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import { GraphCanvas, useNodeDrag } from "./GraphCanvas";
import { STATE_LABEL, type Misconception, type Skill, type SkillState } from "./prepData";
import { loadMapLayout, saveMapLayout, type SkillMap } from "./prepSource";
import styles from "./prep.module.css";

type Props = {
  /** The canonical map: which skills exist, their areas and dependencies (from prepSource) */
  map: SkillMap;
  states: Record<string, SkillState>;
  recall: Record<string, number>;
  misconceptions: Record<string, Misconception[]>;
  /** Skills of the current set get a ring */
  highlight: string[];
  selected: string | null;
  onSelect: (id: string) => void;
  /** What the selected skill opens: shown in a card beside its node, inside the canvas */
  details?: ReactNode;
  onClose: () => void;
};

type Point = { x: number; y: number };

/** One step to the right is one step deeper into the prerequisites */
const COL_W = 210;
/** Skills that sit at the same depth inside one area stack downwards */
const ROW_H = 130;
const NODE = 64;
const NODE_W = 158;
const R = 26;
/** Room for the area name above its lane */
const LANE_HEAD = 24;
const LANE_FOOT = 16;
const LANE_GAP = 14;
const PAD_X = 26;
const TOP = 12;

/** State is shown by shape as well as colour: filled, half, hollow, dashed. */
export function StateGlyph({ state, size = 14 }: { state: SkillState; size?: number }) {
  const r = size / 2 - 1.5;
  const c = size / 2;
  return (
    <svg className={styles.glyph} data-state={state} width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
      {state === "solid" && <circle cx={c} cy={c} r={r} className={styles.glyphFill} />}
      {state === "shaky" && (
        <>
          <circle cx={c} cy={c} r={r} className={styles.glyphRing} />
          <path d={`M${c},${c - r} A${r},${r} 0 0 0 ${c},${c + r} Z`} className={styles.glyphFill} />
        </>
      )}
      {state === "weak" && <circle cx={c} cy={c} r={r} className={styles.glyphRing} />}
      {state === "lowData" && <circle cx={c} cy={c} r={r} className={`${styles.glyphRing} ${styles.glyphDashed}`} />}
    </svg>
  );
}

export function StateLegend() {
  return (
    <ul className={styles.legend} aria-label="Состояния навыков">
      {(Object.keys(STATE_LABEL) as SkillState[]).map((s) => (
        <li key={s}>
          <StateGlyph state={s} />
          {STATE_LABEL[s]}
        </li>
      ))}
      <li>
        <span className={styles.rootTag}>корень</span>
        из-за него ошибки выше
      </li>
    </ul>
  );
}

/** The node itself: the same four shapes as the small glyph, drawn big, with recall as an outer arc. */
function NodeMark({ state, recall }: { state: SkillState; recall: number }) {
  const c = NODE / 2;
  const track = 2 * Math.PI * (R + 5);
  return (
    <svg className={styles.mapShape} width={NODE} height={NODE} viewBox={`0 0 ${NODE} ${NODE}`} aria-hidden="true">
      <circle cx={c} cy={c} r={R + 5} className={styles.mapTrack} />
      <circle
        cx={c}
        cy={c}
        r={R + 5}
        className={styles.mapRecall}
        strokeDasharray={`${(track * recall).toFixed(1)} ${track.toFixed(1)}`}
        transform={`rotate(-90 ${c} ${c})`}
      />
      {state === "solid" && <circle cx={c} cy={c} r={R} className={styles.mapFill} />}
      {state === "shaky" && (
        <>
          <circle cx={c} cy={c} r={R} className={styles.mapRing} />
          <path d={`M${c},${c - R} A${R},${R} 0 0 0 ${c},${c + R} Z`} className={styles.mapFill} />
        </>
      )}
      {state === "weak" && <circle cx={c} cy={c} r={R} className={styles.mapRing} />}
      {state === "lowData" && <circle cx={c} cy={c} r={R} className={`${styles.mapRing} ${styles.mapDashed}`} />}
    </svg>
  );
}

/**
 * The map reads left to right: what a skill rests on stays to its left, what it unlocks to its right.
 * Each exam area keeps its own horizontal lane, so a column means "this deep into the prerequisites".
 */
function autoLayout({ areas, skills }: SkillMap) {
  const byId = new Map(skills.map((s) => [s.id, s]));
  const depths = new Map<string, number>();
  // Data comes from the backend, so a dependency on an unknown skill or a loop must not break the map
  const depth = (s: Skill, seen = new Set<string>()): number => {
    const known = depths.get(s.id);
    if (known !== undefined) return known;
    if (seen.has(s.id)) return 0;
    seen.add(s.id);
    const parents = s.requires.map((id) => byId.get(id)).filter((p): p is Skill => !!p);
    const d = parents.length ? 1 + Math.max(...parents.map((p) => depth(p, seen))) : 0;
    depths.set(s.id, d);
    return d;
  };

  const pos: Record<string, Point> = {};
  const lanes: { area: string; y: number; height: number }[] = [];
  let columns = 1;
  let y = TOP;

  // Areas in the order the map lists them, then any a skill names that the list forgot
  const order = [...areas, ...new Set(skills.map((s) => s.area).filter((a) => !areas.includes(a)))];
  order.forEach((area) => {
    const inArea = skills.filter((s) => s.area === area);
    if (!inArea.length) return;
    const byColumn = new Map<number, Skill[]>();
    inArea.forEach((s) => {
      const col = depth(s);
      columns = Math.max(columns, col + 1);
      byColumn.set(col, [...(byColumn.get(col) ?? []), s]);
    });

    const stack = Math.max(...[...byColumn.values()].map((group) => group.length));
    byColumn.forEach((group, col) => {
      // A short column sits in the middle of the lane rather than hugging its top
      const offset = (stack - group.length) / 2;
      group.forEach((s, i) => {
        pos[s.id] = {
          x: PAD_X + col * COL_W + COL_W / 2,
          y: y + LANE_HEAD + (offset + i) * ROW_H + NODE / 2 + 6,
        };
      });
    });

    const height = LANE_HEAD + stack * ROW_H + LANE_FOOT;
    lanes.push({ area, y, height });
    y += height + LANE_GAP;
  });

  return { pos, lanes, width: PAD_X * 2 + columns * COL_W, height: y };
}

const VIEW_KEY = "lupidrupi.skillmap.view.v1";

const GAP = R + 9;
const HEAD = 6;

/** A point `d` away from `p` in the direction of `towards` — used to cut a link short of the circle. */
function along(p: Point, towards: Point, d: number): Point {
  const vx = towards.x - p.x;
  const vy = towards.y - p.y;
  const len = Math.hypot(vx, vy) || 1;
  return { x: p.x + (vx / len) * d, y: p.y + (vy / len) * d };
}

/**
 * A link between two circles: it leaves to the right and arrives from the left, so the flow of
 * prerequisites stays readable wherever the two nodes have been dragged.
 */
function edgePath(a: Point, b: Point) {
  const reach = Math.max(56, Math.abs(b.x - a.x) * 0.45);
  const c1 = { x: a.x + reach, y: a.y };
  const c2 = { x: b.x - reach, y: b.y };
  const start = along(a, c1, GAP);
  const end = along(b, c2, GAP + HEAD);
  return `M${start.x},${start.y} C${c1.x},${c1.y} ${c2.x},${c2.y} ${end.x},${end.y}`;
}

/** Knowledge map: exam areas as lanes, prerequisites linked to the skill that needs them. */
export function SkillGraph({ map, states, recall, misconceptions, highlight, selected, onSelect, details, onClose }: Props) {
  const { skills } = map;
  const base = useMemo(() => autoLayout(map), [map]);

  // Only the skills the student dragged; the rest keep their automatic place, including skills that
  // arrive later
  const [moved, setMoved] = useState<Record<string, Point>>({});
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    setMoved(loadMapLayout());
    setLoaded(true);
  }, []);

  useEffect(() => {
    if (loaded) saveMapLayout(moved);
  }, [loaded, moved]);

  const pos = useMemo(() => {
    const out = { ...base.pos };
    for (const [id, at] of Object.entries(moved)) if (id in out) out[id] = at;
    return out;
  }, [base, moved]);

  const drag = useNodeDrag((id, x, y) => setMoved((m) => ({ ...m, [id]: { x, y } })));

  const related = new Set<string>();
  const selectedSkill = selected ? skills.find((s) => s.id === selected) : undefined;
  if (selectedSkill) {
    selectedSkill.requires.forEach((id) => related.add(id));
    skills.filter((s) => s.requires.includes(selectedSkill.id)).forEach((s) => related.add(s.id));
  }

  const edges = skills.flatMap((s) => s.requires.filter((from) => from in pos).map((from) => ({ from, to: s.id })));

  return (
    <GraphCanvas
      width={base.width}
      height={base.height}
      label="Холст карты навыков"
      storageKey={VIEW_KEY}
      hint="Нажми на навык — подробности откроются рядом. Узлы и фон двигаются мышкой, Ctrl + колесо — масштаб."
      popover={
        selectedSkill && details
          ? { at: pos[selectedSkill.id], gap: NODE_W / 2, label: selectedSkill.name, content: details, onClose }
          : null
      }
      onBackgroundTap={onClose}
      tools={
        Object.keys(moved).length ? (
          <button type="button" onClick={() => setMoved({})}>
            разложить заново
          </button>
        ) : null
      }
    >
      {base.lanes.map((lane) => (
        <div key={lane.area} className={styles.lane} style={{ top: lane.y, height: lane.height, width: base.width - 24 }}>
          <span className={styles.laneName}>{lane.area}</span>
        </div>
      ))}

      <svg className={styles.graphEdges} width={base.width} height={base.height} aria-hidden="true">
        <defs>
          <marker id="arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M0,0 L8,4 L0,8 Z" className={styles.arrowHead} />
          </marker>
          <marker id="arrow-active" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M0,0 L8,4 L0,8 Z" className={styles.arrowHeadActive} />
          </marker>
        </defs>
        {edges.map(({ from, to }) => {
          const active = selected !== null && (from === selected || to === selected);
          return (
            <path
              key={`${from}-${to}`}
              d={edgePath(pos[from], pos[to])}
              className={`${styles.edge} ${active ? styles.edgeActive : ""}`}
              markerEnd={`url(#${active ? "arrow-active" : "arrow"})`}
            />
          );
        })}
      </svg>

      {skills.map((s) => {
        // A skill the student model has nothing on yet shows as "мало данных", not as an error
        const state = states[s.id] ?? "lowData";
        const recalled = recall[s.id] ?? 0;
        const at = pos[s.id];
        const openMisconceptions = (misconceptions[s.id] ?? []).filter((m) => m.status === "confirmed" || m.status === "suspected").length;
        return (
          <button
            key={s.id}
            type="button"
            className={[
              styles.mapNode,
              highlight.includes(s.id) && styles.mapNodeInSet,
              selected === s.id && styles.mapNodeSelected,
              drag.dragging === s.id && styles.mapNodeDragging,
              selected && selected !== s.id && !related.has(s.id) && styles.mapNodeDim,
            ]
              .filter(Boolean)
              .join(" ")}
            data-state={state}
            style={{ left: at.x - NODE_W / 2, top: at.y - NODE / 2, width: NODE_W }}
            aria-pressed={selected === s.id}
            aria-label={`${s.name}: ${STATE_LABEL[state]}, вспомнит сейчас ${Math.round(recalled * 100)}%, вес ${s.weight}%`}
            title={`${s.name} — ${STATE_LABEL[state]}`}
            {...drag.bind(s.id, at)}
            onClick={() => {
              if (drag.tookOver()) return; // the press ended a drag, not a tap
              onSelect(s.id);
            }}
          >
            <span className={styles.mapShapeBox}>
              <NodeMark state={state} recall={recalled} />
            </span>
            <span className={styles.mapChip}>
              <StateGlyph state={state} size={10} />
              <span className={styles.mapChipName}>{s.name}</span>
            </span>
            <span className={styles.mapFlags}>
              {s.root && <span className={styles.rootTag}>корень</span>}
              {openMisconceptions > 0 && (
                <span className={styles.trapTag} title="Активные заблуждения">
                  ловушка
                </span>
              )}
            </span>
          </button>
        );
      })}
    </GraphCanvas>
  );
}
