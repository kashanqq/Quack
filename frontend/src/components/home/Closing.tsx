"use client";

import Link from "next/link";
import { useEffect, useLayoutEffect, useRef, useState, type AnimationEvent } from "react";
import { PixelDuck } from "@/components/duck/PixelDuck";
import { copy } from "./copy";
import { GROUND, REEDS, SCENE_PALETTE, TREE } from "./HeroLandscape";
import { PixelSprite, type Palette } from "./PixelSprite";
import { Reveal } from "./Reveal";
import styles from "./closing.module.css";

const PALETTE: Palette = {
  ...SCENE_PALETTE,
  h: "#6b4a2b", // hat
  s: "#c98f5e", // skin
  e: "#1e1b19", // eye
  c: "#4d6a7a", // coat
  p: "#3a3a40", // trousers
  B: "#2a2320", // boots
  r: "#7a5230", // rod
  T: "#b08a5a", // rod tip
  R: "#e04b3a", // float, top
  F: "#e8e2d6", // float, bottom
  S: "#9fc3d1", // splash
};

/* The angler faces right, towards the lake. The hand holding the rod is at column 12, row 9. */
const ANGLER = [
  "....hhhhh.....",
  "...hhhhhhh....",
  ".hhhhhhhhhhh..",
  "....sssss.....",
  "....ssses.....",
  "....sssss.....",
  ".....sss......",
  "...ccccccc....",
  "..ccccccccc...",
  "..cccccccccss.",
  "..ccccccccc...",
  "..ccccccccc...",
  "...ccccccc....",
  "...ppppppp....",
  "...ppp.ppp....",
  "...ppp.ppp....",
  "...ppp.ppp....",
  "...ppp.ppp....",
  "...BBB.BBB....",
  "...BBBB.BBBB..",
];

/* The rod runs from the hand (bottom-left) to the tip (top-right). */
const ROD_W = 28;
const ROD_H = 21;

/** A pixel rod, straight or bowed under a catch. The tip stays in the same place either way. */
function rodMap(sag: number): string[] {
  const grid = Array.from({ length: ROD_H }, () => Array<string>(ROD_W).fill("."));
  let prev: number | null = null;
  for (let i = 0; i < ROD_W; i++) {
    const t = i / (ROD_W - 1);
    const y = Math.min(ROD_H - 1, Math.round((ROD_H - 1) * (1 - t) + sag * Math.sin(Math.PI * t)));
    const ch = i > ROD_W - 6 ? "T" : "r";
    grid[y][i] = ch;
    // Fill the gap to the previous column so the rod never breaks up.
    if (prev !== null) for (let yy = Math.min(prev, y) + 1; yy < Math.max(prev, y); yy++) grid[yy][i] = ch;
    prev = y;
  }
  return grid.map((row) => row.join(""));
}

const ROD_STRAIGHT = rodMap(0);
const ROD_BENT = rodMap(3.5);

/** The lake: a long, shallow oval, its surface level with the grass. */
const LAKE = (() => {
  const w = 100;
  const rows = [2, 1, 3, 6].map((pad) => ".".repeat(pad) + "w".repeat(w - pad * 2) + ".".repeat(pad));
  // A few highlights so the water reads as water.
  const put = (row: number, at: number, len: number) => {
    rows[row] = rows[row].slice(0, at) + "W".repeat(len) + rows[row].slice(at + len);
  };
  put(1, 60, 4);
  put(2, 78, 3);
  put(1, 88, 2);
  return rows;
})();

/* The ground tile repeated far wider than any card, then clipped by the scene. */
const GROUND_WIDE = GROUND.map((row) => row.repeat(40));

const FLOAT = ["RR", "RR", "FF", "FF"];
const SPLASH = ["..S......S..", "S..S....S..S", ".S..S..S..S."];

/**
 * The last screen before the footer. Under the summary sits a small pixel lake with
 * an angler. The moment he comes on screen he yanks a duck out of the water and
 * tosses it straight into the "start" button; the duck comes back out of the button
 * towing the next step of the path, hovers, and flies off. Then it all starts again.
 */
export function Closing() {
  const t = copy.closing;
  const sectionRef = useRef<HTMLElement>(null);
  const sceneRef = useRef<HTMLDivElement>(null);
  const ctaRef = useRef<HTMLAnchorElement>(null);
  const waterRef = useRef<HTMLDivElement>(null);
  const flyerRef = useRef<HTMLDivElement>(null);
  // Re-measures the paths to the button; set once the scene is mounted.
  const measureRef = useRef<() => void>(() => {});
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);

  // The show only runs while the scene is on screen, and starts when it first arrives.
  useEffect(() => {
    const el = sceneRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        // Measure right as the show starts, when the layout has surely settled.
        if (entry.isIntersecting) measureRef.current();
        setPlaying(entry.isIntersecting);
      },
      { threshold: 0.4 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // The tossed duck must land in the button and the flag must leave from it, whatever
  // the layout. Measure both paths from the live layout and hand them to the keyframes.
  useEffect(() => {
    const section = sectionRef.current;
    const scene = sceneRef.current;
    const cta = ctaRef.current;
    const water = waterRef.current;
    const flyer = flyerRef.current;
    if (!section || !scene || !cta || !water || !flyer) return;

    const measure = () => {
      if (!sectionRef.current) return;
      const u = parseFloat(getComputedStyle(scene).getPropertyValue("--u")) || 3;
      const b = cta.getBoundingClientRect();
      const bx = b.left + b.width / 2;
      const by = b.top + b.height / 2;
      // The duck waits under water: 16 units wide, centred 40.5 units right of the angler.
      const w = water.getBoundingClientRect();
      const duckX = w.left + 40.5 * u;
      const duckY = w.top + 7 * u;
      // The flyer's resting box; offsets ignore the transform the animation is applying.
      const s = scene.getBoundingClientRect();
      const fx = s.left + flyer.offsetLeft + flyer.offsetWidth / 2;
      const fy = s.top + flyer.offsetTop + flyer.offsetHeight / 2;
      section.style.setProperty("--bx", `${Math.round(bx - duckX)}px`);
      section.style.setProperty("--by", `${Math.round(by - duckY)}px`);
      section.style.setProperty("--fx", `${Math.round(bx - fx)}px`);
      section.style.setProperty("--fy", `${Math.round(by - fy)}px`);
    };

    measureRef.current = measure;
    measure();
    // The section keeps its height while the card inside it grows (fonts, wrapping),
    // so watch the card itself too, and measure again once the web fonts are in.
    const resize = new ResizeObserver(measure);
    resize.observe(section);
    if (scene.parentElement) resize.observe(scene.parentElement);
    resize.observe(flyer);
    let alive = true;
    document.fonts?.ready.then(() => alive && measure());
    return () => {
      alive = false;
      resize.disconnect();
    };
  }, []);

  // Each loop of the flyer brings the next step; the text is swapped while it is hidden.
  const onFlyerLoop = (e: AnimationEvent<HTMLDivElement>) => {
    if (e.target !== e.currentTarget) return;
    setStep((s) => (s + 1) % t.steps.length);
  };

  // A new step changes the flag's size, and with it the path out of the button.
  useLayoutEffect(() => measureRef.current(), [step]);

  const current = t.steps[step];

  return (
    <section
      ref={sectionRef}
      className={styles.section}
      id="about"
      data-play={playing}
      aria-labelledby="closing-heading"
    >
      <Reveal className={styles.card}>
        <p className={styles.kicker}>{t.kicker}</p>
        <h2 id="closing-heading" className={styles.title}>
          {t.title}
        </h2>
        <p className={styles.text}>{t.text}</p>

        {/* The same steps the scene acts out, for screen readers and for reduced motion. */}
        <ol className={styles.steps}>
          {t.steps.map((s, i) => (
            <li key={s.title}>
              <b>
                {i + 1}. {s.title}
              </b>{" "}
              {s.text}
            </li>
          ))}
        </ol>

        <div className={styles.ctaRow}>
          <Link ref={ctaRef} className={styles.cta} href="/choice" data-aura>
            {t.cta}
          </Link>
          <p className={styles.note}>{t.note}</p>
        </div>

        <div ref={sceneRef} className={styles.scene} aria-hidden="true">
          {/* Scenery: dimmed and flat, the way the hero draws it. */}
          <div className={styles.scenery}>
            <PixelSprite className={styles.ground} map={GROUND_WIDE} palette={SCENE_PALETTE} unit={1} />
            <PixelSprite className={styles.tree} map={TREE} palette={PALETTE} unit={1} />
            <PixelSprite className={styles.reedsLeft} map={REEDS} palette={PALETTE} unit={1} />
            <PixelSprite className={styles.reedsRight} map={REEDS} palette={PALETTE} unit={1} />
            <PixelSprite className={styles.lake} map={LAKE} palette={PALETTE} unit={1} />
          </div>

          {/* Everything the angler does is laid out from the spot he stands on. */}
          <div className={styles.rig}>
            <PixelSprite className={styles.angler} map={ANGLER} palette={PALETTE} unit={1} />
            <PixelSprite className={`${styles.rod} ${styles.rodStraight}`} map={ROD_STRAIGHT} palette={PALETTE} unit={1} />
            <PixelSprite className={`${styles.rod} ${styles.rodBent}`} map={ROD_BENT} palette={PALETTE} unit={1} />
            <span className={styles.line} />

            {/* Anything below the waterline is clipped away. */}
            <div ref={waterRef} className={styles.waterline}>
              <PixelSprite className={styles.float} map={FLOAT} palette={PALETTE} unit={1} />
              <div className={styles.hooked}>
                <PixelDuck tempo="fast" />
              </div>
            </div>
            <PixelSprite className={styles.splash} map={SPLASH} palette={PALETTE} unit={1} />
          </div>

          {/* The same duck, back from the sky with the next step in tow. */}
          <div ref={flyerRef} className={styles.flyer} onAnimationIteration={onFlyerLoop}>
            <span className={styles.flyerDuck}>
              <PixelDuck tempo="fast" />
            </span>
            <span className={styles.rope} />
            <span className={styles.flag}>
              <span className={styles.flagNum}>{step + 1}</span>
              <span className={styles.flagTitle}>{current.title}</span>
              <span className={styles.flagText}>{current.text}</span>
            </span>
          </div>
        </div>
      </Reveal>
    </section>
  );
}
