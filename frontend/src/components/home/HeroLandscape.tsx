"use client";

import { useEffect, useRef, useState, type CSSProperties, type RefObject } from "react";
import { PixelDuck, type Tempo } from "@/components/duck/PixelDuck";
import { PixelSprite, pixelRects, type Palette } from "./PixelSprite";
import styles from "./landscape.module.css";

/* Everything in the scene sits on one 4px pixel grid, ducks included. */
const UNIT = 4;

export const SCENE_PALETTE: Palette = {
  t: "#55632f", // grass tufts
  g: "#4b5829", // grass
  G: "#3b4523", // grass, shade
  d: "#332d28", // soil
  D: "#3e3630", // soil, specks
  w: "#2f434c", // water
  W: "#45616d", // water, highlight
  r: "#6a6058", // roof
  f: "#59514a", // frieze
  o: "#3d3732", // trim
  c: "#766c62", // columns
  v: "#35302c", // shadow behind the columns
  y: "#c79d3a", // lit doorway
  s: "#4a433d", // steps
  a: "var(--accent)",
  b: "#8a5a2b", // cattails
  l: "#485829", // leaves
  L: "#39461f", // leaves, shade
  k: "#56402e", // trunk
};

/* A 16-wide strip, tiled across the whole width. Row 1 is the surface. */
export const GROUND = [
  "..t.....t.t.....",
  "gggGgggggggGgggg",
  "GGGGGGGGGGGGGGGG",
  "dddddddDdddddddd",
  "ddDddddddddddDdd",
  "dddddddddddddddd",
];
const SURFACE = (GROUND.length - 1) * UNIT;

const POND = [
  "..wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww..",
  ".wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww.",
  "..wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww..",
  "....wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww....",
];

export const REEDS = [
  ".b..b.",
  ".b..b.",
  ".g..b.",
  ".g.gg.",
  "gg.g..",
  ".g.g.g",
  ".g.g.g",
  ".gg.g.",
  "..g.g.",
  "..ggg.",
];

/* A small columned hall: where the ducks are headed. Column 14 is its centre. */
const HALL = [
  "..............o..............",
  "..............o..............",
  "..............o..............",
  "............rrrrr............",
  "..........rrrrrrrrr..........",
  "........rrrrrrrrrrrrr........",
  "......rrrrrrrrrrrrrrrrr......",
  "....rrrrrrrrrrrrrrrrrrrrr....",
  "..ooooooooooooooooooooooooo..",
  "..fffffffffffffffffffffffff..",
  "..ooooooooooooooooooooooooo..",
  "..vccvvccvvvooooovvvccvvccv..",
  "..vccvvccvvvoyyyovvvccvvccv..",
  "..vccvvccvvvoyyyovvvccvvccv..",
  "..vccvvccvvvoyyyovvvccvvccv..",
  "..vccvvccvvvoyyyovvvccvvccv..",
  ".ooooooooooooooooooooooooooo.",
  "sssssssssssssssssssssssssssss",
];
const HALL_DOOR = 14.5;

export const TREE = [
  "....lllll....",
  "..llllLllll..",
  ".lllLllllLll.",
  ".lllllllllll.",
  "llLllllllLlll",
  "lllllLlllllll",
  "lLllllllllLll",
  ".llllllLllll.",
  "..LLlllllLL..",
  "....LLkLL....",
  "......k......",
  "......k......",
  ".....kkk.....",
];

/* Two frames of the flag on top of the pole, swapped in steps. */
const FLAG_A = ["aaaa.", "aaaaa"];
const FLAG_B = ["aaaaa", "aaaa."];

/** Walking speed on the ground per tempo, px per second. */
const PACE: Record<Tempo, number> = { fast: 80, steady: 48, chill: 28 };
const TEMPOS: Tempo[] = ["fast", "steady", "chill"];

const MIN_GAP = 7000;
const MAX_GAP = 12000;

type Walk = { key: number; tempo: Tempo; toPond: boolean };

const mirror = (easing: string) => (easing === "ease-in" ? "ease-out" : easing === "ease-out" ? "ease-in" : easing);

/**
 * The bottom of the first screen: a strip of pixel ground with a pond on the
 * left and a small hall on the right, dimmed into the background. Every so often a
 * duck walks out of the hall and hops into the pond, or climbs out and walks back.
 */
export function HeroLandscape() {
  const sceneRef = useRef<HTMLDivElement>(null);
  const pondRef = useRef<HTMLDivElement>(null);
  const hallRef = useRef<HTMLDivElement>(null);
  const [walks, setWalks] = useState<Walk[]>([]);
  // Outlives the effect, so a re-run never hands out a key that is still on screen.
  const nextKey = useRef(0);

  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let onScreen = true;
    const observer = new IntersectionObserver((entries) => {
      onScreen = entries.some((e) => e.isIntersecting);
    });
    observer.observe(scene);

    let timer: ReturnType<typeof setTimeout>;
    const schedule = (delay: number) => {
      timer = setTimeout(() => {
        if (onScreen && !document.hidden) {
          const walk = {
            key: nextKey.current++,
            tempo: TEMPOS[Math.floor(Math.random() * TEMPOS.length)],
            toPond: Math.random() < 0.5,
          };
          setWalks((list) => [...list, walk]);
        }
        schedule(MIN_GAP + Math.random() * (MAX_GAP - MIN_GAP));
      }, delay);
    };
    schedule(2500);

    return () => {
      clearTimeout(timer);
      observer.disconnect();
    };
  }, []);

  return (
    <div
      ref={sceneRef}
      className={styles.scene}
      style={{ "--unit": `${UNIT}px`, "--surface": `${SURFACE}px` } as CSSProperties}
      aria-hidden="true"
    >
      {/* The scenery is backdrop: dimmed, and melting into the page at its edges. */}
      <div className={styles.backdrop}>
        <svg className={styles.ground} width="100%" height={GROUND.length * UNIT} shapeRendering="crispEdges">
          <defs>
            <pattern
              id="hero-ground"
              width={GROUND[0].length}
              height={GROUND.length}
              patternUnits="userSpaceOnUse"
              patternTransform={`scale(${UNIT})`}
            >
              {pixelRects(GROUND, SCENE_PALETTE, "g")}
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#hero-ground)" />
        </svg>

        <div ref={pondRef} className={styles.pond}>
          <PixelSprite map={POND} palette={SCENE_PALETTE} unit={UNIT}>
            <rect className={styles.ripple} x={10} y={1} width={4} height={1} fill={SCENE_PALETTE.W} />
            <rect className={styles.ripple} x={30} y={2} width={3} height={1} fill={SCENE_PALETTE.W} />
          </PixelSprite>
          {/* Only the top of the swimmer shows above the water line. */}
          <div className={styles.swim}>
            <div className={styles.swimmer}>
              <PixelDuck tempo="chill" />
            </div>
          </div>
        </div>

        <PixelSprite className={styles.reedsLeft} map={REEDS} palette={SCENE_PALETTE} unit={UNIT} />
        <PixelSprite className={styles.reedsRight} map={REEDS} palette={SCENE_PALETTE} unit={UNIT} />
        <PixelSprite className={styles.treeLeft} map={TREE} palette={SCENE_PALETTE} unit={UNIT} />
        <PixelSprite className={styles.treeRight} map={TREE} palette={SCENE_PALETTE} unit={UNIT} />

        <div ref={hallRef} className={styles.hall}>
          <PixelSprite map={HALL} palette={SCENE_PALETTE} unit={UNIT}>
            <g className={styles.flagA} transform="translate(15 0)">
              {pixelRects(FLAG_A, SCENE_PALETTE, "fa")}
            </g>
            <g className={styles.flagB} transform="translate(15 0)">
              {pixelRects(FLAG_B, SCENE_PALETTE, "fb")}
            </g>
          </PixelSprite>
        </div>
      </div>

      {walks.map((walk) => (
        <Walker
          key={walk.key}
          tempo={walk.tempo}
          toPond={walk.toPond}
          sceneRef={sceneRef}
          pondRef={pondRef}
          hallRef={hallRef}
          onDone={() => setWalks((list) => list.filter((w) => w.key !== walk.key))}
        />
      ))}
    </div>
  );
}

type WalkerProps = Omit<Walk, "key"> & {
  sceneRef: RefObject<HTMLDivElement | null>;
  pondRef: RefObject<HTMLDivElement | null>;
  hallRef: RefObject<HTMLDivElement | null>;
  onDone: () => void;
};

/** One duck commuting between the hall door and the pond, in either direction. */
function Walker({ tempo, toPond, sceneRef, pondRef, hallRef, onDone }: WalkerProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    const scene = sceneRef.current?.getBoundingClientRect();
    const pond = pondRef.current?.getBoundingClientRect();
    const hall = hallRef.current?.getBoundingClientRect();
    // The hall is hidden on narrow screens, and then there is nowhere to walk to.
    if (!el || !scene || !pond || !hall || !hall.width) return onDone();

    const w = el.offsetWidth;
    const door = hall.left - scene.left + HALL_DOOR * UNIT;
    const shore = pond.right - scene.left - 8 * UNIT;
    const bank = shore + 10 * UNIT;
    const walkMs = (Math.abs(door - bank) / PACE[tempo]) * 1000;

    // x is the duck's centre, y how far above the surface its feet are.
    const at = (x: number, y: number, opacity: number, easing = "linear") => ({
      transform: `translate(${x - w / 2}px, ${-y}px)`,
      opacity,
      easing,
    });
    // In the hall's doorway, on the bank, in the air over the water, under it.
    const route = [
      { ...at(door, 0, 0), ms: 0 },
      { ...at(door - 3 * UNIT, 0, 1), ms: 500 },
      { ...at(bank, 0, 1, "ease-out"), ms: walkMs },
      { ...at((bank + shore) / 2, 7 * UNIT, 1, "ease-in"), ms: 260 },
      { ...at(shore, -4 * UNIT, 0), ms: 320 },
    ];
    // Walked backwards, each segment keeps its length and its easing flips.
    const n = route.length;
    const steps = toPond
      ? route
      : route.map((_, i) => ({
          ...route[n - 1 - i],
          easing: mirror(route[n - 2 - i]?.easing ?? "linear"),
          ms: i === 0 ? 0 : route[n - i].ms,
        }));

    const total = steps.reduce((sum, s) => sum + s.ms, 0);
    let t = 0;
    const frames = steps.map(({ ms, ...frame }) => {
      t += ms;
      return { ...frame, offset: t / total };
    });

    const animation = el.animate(frames, { duration: total, fill: "forwards" });
    animation.onfinish = onDone;
    return () => animation.cancel();
    // A walk is planned once, when the duck sets out.
  }, []);

  return (
    <div ref={ref} className={styles.walker} data-facing={toPond ? "left" : "right"}>
      <PixelDuck tempo={tempo} />
    </div>
  );
}
