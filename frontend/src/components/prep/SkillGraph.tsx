"use client";

import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { store } from "../account/store";
import { GraphCanvas, useNodeDrag, useVertical } from "./GraphCanvas";
import { AREAS, SKILLS, STATE_LABEL, type Misconception, type Skill, type SkillState } from "./prepData";
import styles from "./prep.module.css";

type Props = {
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

/**
 * Phones: the same map turned to run top to bottom. Areas stack as sections, one step down is one step
 * deeper into the prerequisites, and skills at the same depth sit side by side.
 */
const V_COL_W = 150;
/** Circle, a two-line label, the flags, and room for the links to curve in between */
const V_ROW_H = 176;
const V_NODE_W = 142;
const V_PAD_X = 6;

type Orientation = "horizontal" | "vertical";

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
 * On a phone it reads top to bottom instead (see verticalLayout).
 */
function autoLayout(orientation: Orientation) {
  return orientation === "vertical" ? verticalLayout() : horizontalLayout();
}

const depthOf = (s: Skill): number =>
  s.requires.length ? 1 + Math.max(...s.requires.map((id) => depthOf(SKILLS.find((k) => k.id === id)!))) : 0;

type Lane = { area: string; x: number; y: number; width: number; height: number };

function horizontalLayout() {
  const depth = depthOf;
  const pos: Record<string, Point> = {};
  const lanes: Lane[] = [];
  let columns = 0;
  let y = TOP;

  AREAS.forEach((area) => {
    const byColumn = new Map<number, Skill[]>();
    SKILLS.filter((s) => s.area === area).forEach((s) => {
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
    lanes.push({ area, x: 12, y, width: 0, height });
    y += height + LANE_GAP;
  });

  const width = PAD_X * 2 + columns * COL_W;
  return { pos, lanes: lanes.map((l) => ({ ...l, width: width - 24 })), width, height: y };
}

function verticalLayout() {
  const areas = AREAS.map((area) => {
    const byRow = new Map<number, Skill[]>();
    SKILLS.filter((s) => s.area === area).forEach((s) => byRow.set(depthOf(s), [...(byRow.get(depthOf(s)) ?? []), s]));
    // Rows are the depths this area actually has, so an area that starts deep does not open on a gap
    return { area, rows: [...byRow.entries()].sort(([a], [b]) => a - b).map(([, group]) => group) };
  });
  const columns = Math.max(...areas.flatMap((a) => a.rows.map((group) => group.length)));
  const width = V_PAD_X * 2 + columns * V_COL_W;

  const pos: Record<string, Point> = {};
  const lanes: Lane[] = [];
  let y = TOP;
  areas.forEach(({ area, rows }) => {
    if (!rows.length) return;
    rows.forEach((group, row) => {
      // A row with fewer skills sits in the middle of the section
      const offset = (columns - group.length) / 2;
      group.forEach((s, i) => {
        pos[s.id] = { x: V_PAD_X + (offset + i) * V_COL_W + V_COL_W / 2, y: y + LANE_HEAD + row * V_ROW_H + NODE / 2 + 6 };
      });
    });
    const height = LANE_HEAD + rows.length * V_ROW_H - 20 + LANE_FOOT;
    lanes.push({ area, x: 2, y, width: width - 4, height });
    y += height + LANE_GAP;
  });

  return { pos, lanes, width, height: y };
}

const BASE: Record<Orientation, ReturnType<typeof horizontalLayout>> = {
  horizontal: autoLayout("horizontal"),
  vertical: autoLayout("vertical"),
};
/** Each orientation keeps its own arrangement: a node dragged on the phone map says nothing about the wide one */
const NODES_KEY: Record<Orientation, string> = {
  horizontal: "lupidrupi.skillmap.nodes.v1",
  vertical: "lupidrupi.skillmap.nodes.vertical.v1",
};
const VIEW_KEY: Record<Orientation, string> = {
  horizontal: "lupidrupi.skillmap.view.v1",
  vertical: "lupidrupi.skillmap.view.vertical.v1",
};

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

/**
 * The same link on the phone map: it leaves from under the whole node — circle, label and flags, `foot`
 * below the centre — and comes down onto the top of the next circle, so it never runs through a label.
 * A link that jumps over rows would cut through the skills in between, so it takes the margin instead:
 * out to `margin`, down the edge of the map, and back in above its target.
 */
function edgePathDown(a: Point, b: Point, foot: number, margin: number) {
  const start = { x: a.x, y: a.y + foot + 4 };
  const end = { x: b.x, y: b.y - GAP - HEAD };
  if (end.y - start.y > V_ROW_H) {
    const bend = 28;
    return [
      `M${start.x},${start.y}`,
      `C${start.x},${start.y + bend} ${margin},${start.y + bend} ${margin},${start.y + bend * 2}`,
      `L${margin},${end.y - bend * 2}`,
      `C${margin},${end.y - bend} ${end.x},${end.y - bend} ${end.x},${end.y}`,
    ].join(" ");
  }
  const reach = Math.max(24, Math.abs(end.y - start.y) * 0.45);
  return `M${start.x},${start.y} C${start.x},${start.y + reach} ${end.x},${end.y - reach} ${end.x},${end.y}`;
}

/** Knowledge map: exam areas as lanes, prerequisites linked to the skill that needs them. */
export function SkillGraph({ states, recall, misconceptions, highlight, selected, onSelect, details, onClose }: Props) {
  const orientation: Orientation = useVertical() ? "vertical" : "horizontal";
  const vertical = orientation === "vertical";
  const base = BASE[orientation];
  const nodeW = vertical ? V_NODE_W : NODE_W;

  // Only the nodes the student dragged, per orientation; everything else keeps its automatic place
  const [moved, setMoved] = useState<Record<Orientation, Record<string, Point>>>({ horizontal: {}, vertical: {} });
  // Saved when a node is let go (or the layout is reset), never while it is being dragged
  const [commits, setCommits] = useState(0);
  const movedRef = useRef(moved);
  movedRef.current = moved;

  useEffect(() => {
    const load = (o: Orientation) =>
      Object.fromEntries(Object.entries(store.get<Record<string, Point>>(NODES_KEY[o]) ?? {}).filter(([id]) => id in BASE[o].pos));
    setMoved({ horizontal: load("horizontal"), vertical: load("vertical") });
  }, []);

  useEffect(() => {
    if (!commits) return;
    const o = movedRef.current[orientation];
    store.set(NODES_KEY[orientation], Object.keys(o).length ? o : null);
  }, [commits, orientation]);

  const pos = { ...base.pos, ...moved[orientation] };
  const hasMoved = Object.keys(moved[orientation]).length > 0;

  const drag = useNodeDrag(
    (id, x, y) => setMoved((m) => ({ ...m, [orientation]: { ...m[orientation], [id]: { x, y } } })),
    () => setCommits((c) => c + 1)
  );
  const resetLayout = () => {
    setMoved((m) => ({ ...m, [orientation]: {} }));
    setCommits((c) => c + 1);
  };

  // On the phone map links start under each node, so how far down a node reaches is measured, not guessed
  const nodeRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const [feet, setFeet] = useState<Record<string, number>>({});
  useLayoutEffect(() => {
    if (!vertical) return;
    const next: Record<string, number> = {};
    for (const [id, el] of Object.entries(nodeRefs.current)) if (el) next[id] = el.offsetHeight - NODE / 2;
    if (Object.entries(next).some(([id, f]) => feet[id] !== f)) setFeet(next);
  });

  const related = new Set<string>();
  if (selected) {
    const skill = SKILLS.find((s) => s.id === selected)!;
    skill.requires.forEach((id) => related.add(id));
    SKILLS.filter((s) => s.requires.includes(selected)).forEach((s) => related.add(s.id));
  }

  const edges = SKILLS.flatMap((s) => s.requires.map((from) => ({ from, to: s.id })));

  return (
    <GraphCanvas
      width={base.width}
      height={base.height}
      label="Холст карты навыков"
      storageKey={VIEW_KEY[orientation]}
      hint={
        vertical
          ? "Нажми на навык — подробности снизу. Карта листается пальцем."
          : "Нажми на навык — подробности откроются рядом. Узлы и фон двигаются мышкой, Ctrl + колесо — масштаб."
      }
      popover={
        selected && details
          ? { at: pos[selected], gap: nodeW / 2, label: SKILLS.find((s) => s.id === selected)!.name, content: details, onClose }
          : null
      }
      onBackgroundTap={onClose}
      beacons={[
        // Roots first: errors higher up trace back to them. Then skills with a confirmed trap.
        ...SKILLS.filter((s) => s.root).map((s) => ({ id: s.id, at: pos[s.id], label: `Корень: ${s.name}`, tone: "root" as const })),
        ...SKILLS.filter((s) => misconceptions[s.id].some((m) => m.status === "confirmed")).map((s) => ({
          id: s.id,
          at: pos[s.id],
          label: `Ловушка: ${s.name}`,
          tone: "trap" as const,
        })),
      ]}
      tools={
        hasMoved ? (
          <button type="button" onClick={resetLayout}>
            разложить заново
          </button>
        ) : null
      }
    >
      {base.lanes.map((lane) => (
        <div key={lane.area} className={styles.lane} style={{ left: lane.x, top: lane.y, height: lane.height, width: lane.width }}>
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
              d={vertical ? edgePathDown(pos[from], pos[to], feet[from] ?? NODE / 2 + 80, base.width - 3) : edgePath(pos[from], pos[to])}
              className={`${styles.edge} ${active ? styles.edgeActive : ""}`}
              markerEnd={`url(#${active ? "arrow-active" : "arrow"})`}
            />
          );
        })}
      </svg>

      {SKILLS.map((s) => {
        const state = states[s.id];
        const at = pos[s.id];
        const openMisconceptions = misconceptions[s.id].filter((m) => m.status === "confirmed" || m.status === "suspected").length;
        return (
          <button
            key={s.id}
            ref={(el) => {
              nodeRefs.current[s.id] = el;
            }}
            type="button"
            className={[
              styles.mapNode,
              highlight.includes(s.id) && styles.mapNodeInSet,
              s.root && styles.mapNodeRoot,
              selected === s.id && styles.mapNodeSelected,
              drag.dragging === s.id && styles.mapNodeDragging,
              selected && selected !== s.id && !related.has(s.id) && styles.mapNodeDim,
            ]
              .filter(Boolean)
              .join(" ")}
            data-state={state}
            style={{ left: at.x - nodeW / 2, top: at.y - NODE / 2, width: nodeW }}
            aria-pressed={selected === s.id}
            aria-label={`${s.name}: ${STATE_LABEL[state]}, вспомнит сейчас ${Math.round(recall[s.id] * 100)}%, вес ${s.weight}%`}
            title={`${s.name} — ${STATE_LABEL[state]}`}
            {...drag.bind(s.id, at)}
            onClick={() => {
              if (drag.tookOver()) return; // the press ended a drag, not a tap
              onSelect(s.id);
            }}
          >
            <span className={styles.mapShapeBox}>
              <NodeMark state={state} recall={recall[s.id]} />
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
