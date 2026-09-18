"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";
import { PixelDuck, type Tempo } from "./PixelDuck";
import { pixelRects } from "./PixelSprite";
import styles from "./duck-lane.module.css";

/* Props are drawn on the same 16-wide pixel grid as the duck, so they line up. */
const COLORS: Record<string, string> = {
  o: "var(--duck-outline)",
  a: "var(--accent)",
  y: "var(--duck-body)",
  s: "rgba(255,255,255,0.4)",
};

const PARACHUTE = [
  "....aaaaaaaa....",
  "..aaaaaaaaaaaa..",
  ".aaaaaaaaaaaaaa.",
  ".aaaaaaaaaaaaaa.",
  "..s..s....s..s..",
  "...s..s..s..s...",
  "....s..s.s..s...",
  ".....s.s.s.s....",
  "......ss.ss.....",
];

const BALLOON = [
  ".....yyyyyy.....",
  "...yyyyyyyyyy...",
  "..yyyyyyyyyyyy..",
  "..yyyyyyyyyyyy..",
  "...yyyyyyyyyy...",
  ".....yyyyyy.....",
  "......y..y......",
  ".......ss.......",
  "........s.......",
  ".......s........",
  "........s.......",
];

const ROPE = [
  "........s.......",
  "........s.......",
  ".......s........",
  "........s.......",
  "........s.......",
  ".......s........",
  "........s.......",
  "......ooo.......",
];

const FLAME = [
  "......aaaa......",
  ".....aayyaa.....",
  "......ayya......",
  ".......aa.......",
];

function Prop({ map, name }: { map: string[]; name: string }) {
  return (
    <svg className={styles.prop} viewBox={`0 0 16 ${map.length}`} shapeRendering="crispEdges" aria-hidden="true">
      {pixelRects(map, COLORS, name)}
    </svg>
  );
}

type Vignette = {
  id: string;
  /** "down" falls from the top, "up" climbs from the bottom. */
  dir: "down" | "up";
  /** Seconds to cross the lane. */
  seconds: number;
  tempo: Tempo;
  above?: string[];
  below?: string[];
  /** Adds a slow tumble, for the ones that are not in control. */
  tumble?: boolean;
};

/* Small gags, each with its own speed. Nothing here is a status or a score —
   they are just ducks having a day. */
const VIGNETTES: Vignette[] = [
  { id: "parachute", dir: "down", seconds: 13, tempo: "chill", above: PARACHUTE },
  { id: "freefall", dir: "down", seconds: 6, tempo: "fast", tumble: true },
  { id: "climber", dir: "up", seconds: 14, tempo: "steady", above: ROPE },
  { id: "balloon", dir: "up", seconds: 16, tempo: "chill", above: BALLOON },
  { id: "rocket", dir: "up", seconds: 5.5, tempo: "fast", below: FLAME },
];

/** Gap between two ducks, in milliseconds. */
const MIN_GAP = 5000;
const MAX_GAP = 9000;

type Flight = Vignette & { key: number; lane: number };

type DuckLaneProps = {
  /** Ducks only launch while the section is on screen. */
  active: boolean;
  /** Which edge of the section the lane runs down. */
  side?: "left" | "right";
  /** Delay before the first duck, so two lanes do not launch in step. */
  firstDelay?: number;
};

/** A narrow lane down one edge where ducks drift past, up or down. */
export function DuckLane({ active, side = "right", firstDelay = 1200 }: DuckLaneProps) {
  const [flights, setFlights] = useState<Flight[]>([]);
  // Outlives the effect: it re-runs each time the section comes back on screen, while
  // ducks from the last run may still be in the air.
  const nextKey = useRef(0);

  useEffect(() => {
    if (!active) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let timer: ReturnType<typeof setTimeout>;
    let previous = -1;

    const launch = () => {
      // Never the same gag twice in a row.
      let i = Math.floor(Math.random() * VIGNETTES.length);
      if (i === previous) i = (i + 1) % VIGNETTES.length;
      previous = i;
      setFlights((list) => [...list, { ...VIGNETTES[i], key: nextKey.current++, lane: Math.random() }]);
    };

    const schedule = (delay: number) => {
      timer = setTimeout(() => {
        if (!document.hidden) launch();
        schedule(MIN_GAP + Math.random() * (MAX_GAP - MIN_GAP));
      }, delay);
    };

    schedule(firstDelay);
    return () => clearTimeout(timer);
  }, [active, firstDelay]);

  return (
    <div className={styles.lane} data-side={side} aria-hidden="true">
      {flights.map((flight) => (
        <div
          key={flight.key}
          className={styles.flight}
          data-dir={flight.dir}
          style={
            {
              "--seconds": `${flight.seconds}s`,
              "--lane": flight.lane,
            } as CSSProperties
          }
          onAnimationEnd={(e) => {
            if (e.target === e.currentTarget) {
              setFlights((list) => list.filter((f) => f.key !== flight.key));
            }
          }}
        >
          <div className={styles.sway}>
            <div className={flight.tumble ? styles.tumble : undefined}>
              {flight.above && <Prop map={flight.above} name={flight.id} />}
              <PixelDuck tempo={flight.tempo} />
              {flight.below && <Prop map={flight.below} name={`${flight.id}-b`} />}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
