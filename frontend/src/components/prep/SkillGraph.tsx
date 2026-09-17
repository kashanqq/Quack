"use client";

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
};

const COL_W = 212;
const NODE_W = 184;
const NODE_H = 86;
const ROW_H = 116;
const TOP = 44;

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

function layout() {
  const pos: Record<string, { x: number; y: number }> = {};
  const depth = (s: Skill): number => (s.requires.length ? 1 + Math.max(...s.requires.map((id) => depth(SKILLS.find((k) => k.id === id)!))) : 0);
  AREAS.forEach((area, col) => {
    SKILLS.filter((s) => s.area === area)
      .sort((a, b) => depth(a) - depth(b))
      .forEach((s, row) => {
        pos[s.id] = { x: col * COL_W + (COL_W - NODE_W) / 2, y: TOP + row * ROW_H };
      });
  });
  return pos;
}

const POS = layout();
const WIDTH = AREAS.length * COL_W;
const HEIGHT = TOP + Math.max(...Object.values(POS).map((p) => p.y)) + NODE_H + 16;

/** Knowledge map: exam areas as columns, prerequisites as arrows pointing to the skill that needs them. */
export function SkillGraph({ states, recall, misconceptions, highlight, selected, onSelect }: Props) {
  const related = new Set<string>();
  if (selected) {
    const skill = SKILLS.find((s) => s.id === selected)!;
    skill.requires.forEach((id) => related.add(id));
    SKILLS.filter((s) => s.requires.includes(selected)).forEach((s) => related.add(s.id));
  }

  const edges = SKILLS.flatMap((s) => s.requires.map((from) => ({ from, to: s.id })));

  return (
    <div className={styles.graphScroll}>
      <div className={styles.graph} style={{ width: WIDTH, height: HEIGHT }}>
        {AREAS.map((area, col) => (
          <div key={area} className={styles.graphArea} style={{ left: col * COL_W, width: COL_W }}>
            {area}
          </div>
        ))}

        <svg className={styles.graphEdges} width={WIDTH} height={HEIGHT} aria-hidden="true">
          <defs>
            <marker id="arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M0,0 L8,4 L0,8 Z" className={styles.arrowHead} />
            </marker>
            <marker id="arrow-active" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M0,0 L8,4 L0,8 Z" className={styles.arrowHeadActive} />
            </marker>
          </defs>
          {edges.map(({ from, to }) => {
            const a = POS[from];
            const b = POS[to];
            const sameColumn = Math.abs(a.x - b.x) < 1;
            const d = sameColumn
              ? // Down the column, bowing out to the left so it clears nodes in between
                `M${a.x + 18},${a.y + NODE_H} C${a.x - 14},${a.y + NODE_H + 30} ${b.x - 14},${b.y - 30} ${b.x + 18},${b.y}`
              : `M${a.x + NODE_W},${a.y + NODE_H / 2} C${a.x + NODE_W + 40},${a.y + NODE_H / 2} ${b.x - 40},${b.y + NODE_H / 2} ${b.x},${b.y + NODE_H / 2}`;
            const active = selected !== null && (from === selected || to === selected);
            return (
              <path
                key={`${from}-${to}`}
                d={d}
                className={`${styles.edge} ${active ? styles.edgeActive : ""}`}
                markerEnd={`url(#${active ? "arrow-active" : "arrow"})`}
              />
            );
          })}
        </svg>

        {SKILLS.map((s) => {
          const state = states[s.id];
          const openMisconceptions = misconceptions[s.id].filter((m) => m.status === "confirmed" || m.status === "suspected").length;
          return (
            <button
              key={s.id}
              type="button"
              className={[
                styles.node,
                highlight.includes(s.id) && styles.nodeInSet,
                selected === s.id && styles.nodeSelected,
                selected && selected !== s.id && !related.has(s.id) && styles.nodeDim,
              ]
                .filter(Boolean)
                .join(" ")}
              data-state={state}
              style={{ left: POS[s.id].x, top: POS[s.id].y, width: NODE_W, height: NODE_H }}
              aria-pressed={selected === s.id}
              aria-label={`${s.name}: ${STATE_LABEL[state]}, вес ${s.weight}%`}
              onClick={() => onSelect(s.id)}
            >
              <span className={styles.nodeTop}>
                <StateGlyph state={state} />
                <span className={styles.nodeName}>{s.name}</span>
              </span>
              <span className={styles.nodeMeta}>
                <span>{STATE_LABEL[state]}</span>
                <span>вес {s.weight}%</span>
                {s.root && <span className={styles.rootTag}>корень</span>}
                {openMisconceptions > 0 && (
                  <span className={styles.trapTag} title="Активные заблуждения">
                    ловушка
                  </span>
                )}
              </span>
              <span className={styles.recall} aria-hidden="true">
                <span style={{ width: `${Math.round(recall[s.id] * 100)}%` }} />
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
