import type { CSSProperties } from "react";
import styles from "./pixel-duck.module.css";

/* The duck is a 16x14 char grid drawn as one <rect> per horizontal run of colour.
   Body, wing and feet are separate layers so each can animate on its own beat. */

const W = 16;
const H = 14;

const BODY = [
  "................",
  "........oooo....",
  ".......obbbbo...",
  ".......obebbo...",
  ".......obbbbokkk",
  ".......obbbbokk.",
  "......oobbbboo..",
  "...oooobbbbbboo.",
  ".oobbbbbbbbbbbo.",
  "obbbbbbbbbbbbbo.",
  ".obbbbbbbbbbbo..",
  "..obbbbbbbbbbo..",
  "...oooooooooo...",
  "................",
];

const WING = [
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
  "....ossssso.....",
  "...ossssssso....",
  "....ooooooo.....",
  "................",
  "................",
];

const FEET = [
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
  "....kko..kko....",
];

const COLORS: Record<string, string> = {
  o: "var(--duck-outline)",
  e: "var(--duck-outline)",
  b: "var(--duck-body)",
  s: "var(--duck-wing)",
  k: "var(--duck-beak)",
};

/** Collapse each row into runs of one colour, so a duck is ~30 rects instead of 224. */
function pixels(map: string[], keyPrefix: string) {
  const rects = [];
  for (let y = 0; y < H; y++) {
    const row = map[y];
    let x = 0;
    while (x < W) {
      const ch = row[x];
      if (ch === "." || !COLORS[ch]) {
        x++;
        continue;
      }
      let run = 1;
      while (x + run < W && row[x + run] === ch) run++;
      rects.push(
        <rect key={`${keyPrefix}-${x}-${y}`} x={x} y={y} width={run} height={1} fill={COLORS[ch]} />
      );
      x += run;
    }
  }
  return rects;
}

export type Tempo = "fast" | "steady" | "chill";

/* One beat of the idle animation. Everything else is derived from it. */
const BEAT: Record<Tempo, string> = {
  fast: "0.26s",
  steady: "0.5s",
  chill: "0.95s",
};

type PixelDuckProps = {
  tempo?: Tempo;
  className?: string;
};

/**
 * Flat pixel-art duck. `tempo` only changes how fast it bobs and flaps — the same
 * duck, moving at its own speed.
 */
export function PixelDuck({ tempo = "steady", className }: PixelDuckProps) {
  return (
    <svg
      className={[styles.duck, className].filter(Boolean).join(" ")}
      style={{ "--beat": BEAT[tempo] } as CSSProperties}
      viewBox={`0 0 ${W} ${H}`}
      shapeRendering="crispEdges"
      aria-hidden="true"
    >
      <g className={styles.bob}>
        <g>{pixels(BODY, "b")}</g>
        <g className={styles.wing}>{pixels(WING, "w")}</g>
      </g>
      <g className={styles.feet}>{pixels(FEET, "f")}</g>
    </svg>
  );
}
