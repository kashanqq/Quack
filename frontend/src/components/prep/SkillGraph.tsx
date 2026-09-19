"use client";

// Topic state marks: a small glyph for lists and a big node for the set graph. Both use shape as well
// as colour, so the state reads without a legend.

import type { SkillState } from "./prepData";
import styles from "./prep.module.css";

const NODE = 64;
const R = 26;

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

/** The node itself: the same four shapes as the small glyph, drawn big, with recall as an outer arc. */
export function NodeMark({ state, recall }: { state: SkillState; recall: number }) {
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
