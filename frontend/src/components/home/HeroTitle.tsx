"use client";

import { useEffect, useRef } from "react";
import { PixelDuck } from "@/components/duck/PixelDuck";
import styles from "./home.module.css";

const WORD = "Quack";
const MARK = "!";

/** Duck size in duck-pixels (the PixelDuck grid). */
const DUCK_W = 16;
const DUCK_H = 14;

/** Walking speed along the letters, px per second. */
const WALK = 70;
const HOP_MS = 460;
/** Letters whose tops differ by less than this are walked across without a hop. */
const FLAT = 5;

const FIRST_MS = 3500;
const MIN_GAP = 20000;
const MAX_GAP = 30000;

type Point = { x: number; y: number; opacity: number; easing: string; ms: number };

/**
 * The hero title with a pixel duck that now and then drops onto the "Q", walks
 * along the tops of the letters (hopping where they change height), jumps off the
 * "!" and waddles away.
 */
export function HeroTitle() {
  const titleRef = useRef<HTMLHeadingElement>(null);
  const probeRef = useRef<HTMLSpanElement>(null);
  const duckRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const title = titleRef.current;
    const probe = probeRef.current;
    const duck = duckRef.current;
    if (!title || !probe || !duck) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let onScreen = true;
    const observer = new IntersectionObserver((entries) => {
      onScreen = entries.some((e) => e.isIntersecting);
    });
    observer.observe(title);

    let timer: ReturnType<typeof setTimeout>;
    let running: Animation | null = null;

    const walk = () => {
      const path = measurePath(title, probe);
      if (!path) return;
      duck.style.width = `${path.w}px`;
      duck.style.height = `${path.h}px`;
      const total = path.points.reduce((sum, p) => sum + p.ms, 0);
      let at = 0;
      const frames = path.points.map((p) => {
        at += p.ms;
        return {
          offset: at / total,
          transform: `translate(${p.x - path.w / 2}px, ${p.y - path.h}px)`,
          opacity: p.opacity,
          easing: p.easing,
        };
      });
      running = duck.animate(frames, { duration: total });
    };

    const schedule = (delay: number) => {
      timer = setTimeout(() => {
        if (onScreen && !document.hidden) walk();
        schedule(MIN_GAP + Math.random() * (MAX_GAP - MIN_GAP));
      }, delay);
    };

    let cancelled = false;
    document.fonts.ready.then(() => {
      if (!cancelled) schedule(FIRST_MS);
    });

    return () => {
      cancelled = true;
      clearTimeout(timer);
      observer.disconnect();
      running?.cancel();
    };
  }, []);

  return (
    <h1 ref={titleRef} className={styles.title}>
      <span ref={probeRef} className={styles.titleProbe} aria-hidden="true" />
      {WORD}
      <span className={styles.accent}>{MARK}</span>
      <span ref={duckRef} className={styles.titleDuck} aria-hidden="true">
        <PixelDuck tempo="steady" />
      </span>
    </h1>
  );
}

/**
 * Works out where the tops of the glyphs are, in the title's own coordinates,
 * and turns them into a route for the duck: points are the duck's bottom centre.
 */
function measurePath(title: HTMLElement, probe: HTMLElement) {
  const cs = getComputedStyle(title);
  const ctx = document.createElement("canvas").getContext("2d");
  if (!ctx) return null;
  ctx.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;

  // The probe is an empty inline-block, so its box sits exactly on the baseline.
  const box = title.getBoundingClientRect();
  const at = probe.getBoundingClientRect();
  const originX = at.left - box.left;
  const baseline = at.top - box.top;

  const fontSize = parseFloat(cs.fontSize);
  const unit = Math.max(2, Math.round(fontSize / 30));
  const w = DUCK_W * unit;
  const h = DUCK_H * unit;

  // Glyph ink per letter; the face is monospaced, so letters sit on a fixed advance.
  let x = originX;
  const glyphs = [...(WORD + MARK)].map((ch) => {
    const m = ctx.measureText(ch);
    const g = { left: x - m.actualBoundingBoxLeft, right: x + m.actualBoundingBoxRight, top: baseline - m.actualBoundingBoxAscent };
    x += m.width;
    return g;
  });

  // Neighbouring letters of the same height form one stretch of "ground".
  const runs: { left: number; right: number; top: number }[] = [];
  for (const g of glyphs) {
    const last = runs[runs.length - 1];
    if (last && Math.abs(last.top - g.top) < FLAT) {
      last.right = g.right;
      last.top = Math.min(last.top, g.top);
    } else {
      runs.push({ ...g });
    }
  }

  const inset = w * 0.3;
  const ends = runs.map((r) => {
    const mid = (r.left + r.right) / 2;
    const from = Math.min(r.left + inset, mid);
    const to = Math.max(r.right - inset, mid);
    return { from, to, top: r.top };
  });

  const points: Point[] = [];
  const add = (px: number, py: number, ms: number, opacity = 1, easing = "linear") =>
    points.push({ x: px, y: py, ms, opacity, easing });
  const walkMs = (a: number, b: number) => (Math.abs(b - a) / WALK) * 1000;

  // Drop in from above onto the first letter.
  const first = ends[0];
  add(first.from, first.top - h * 2.2, 0, 0, "cubic-bezier(0.5, 0, 1, 1)");
  add(first.from, first.top, 520);

  ends.forEach((run, i) => {
    add(run.to, run.top, walkMs(run.from, run.to));
    const next = ends[i + 1];
    if (!next) return;
    // Rise out of the take-off, fall into the landing.
    const apex = Math.min(run.top, next.top) - h * 0.55;
    points[points.length - 1].easing = "ease-out";
    add((run.to + next.from) / 2, apex, HOP_MS / 2, 1, "ease-in");
    add(next.from, next.top, HOP_MS / 2);
  });

  // Jump off the "!" down to the baseline, then waddle off and fade.
  const last = ends[ends.length - 1];
  const land = last.to + w * 1.1;
  points[points.length - 1].easing = "ease-out";
  add((last.to + land) / 2, last.top - h * 0.6, 320, 1, "ease-in");
  add(land, baseline, 420);
  add(land + w * 1.6, baseline, walkMs(0, w * 1.6), 0);

  return { points, w, h };
}
