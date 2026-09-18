"use client";

import { useEffect, useRef } from "react";
import styles from "./aura.module.css";

/* Tile pitch in CSS pixels and the gap left between neighbouring tiles. */
const CELL = 30;
const GAP = 3;
/* Radius of the patch of tiles the pointer wakes up, at rest and over something interactive. */
const RADIUS = [230, 290];
/* How high a fully raised tile floats above the page, in pixels. */
const LIFT = 7;
/* Peak fill opacity of a fully raised tile; the shadow beneath it is a fraction of that. */
const TILE_ALPHA = 0.42;
const SHADOW_ALPHA = 0.55;
/* Pointer easing per frame — the patch trails the cursor instead of snapping to it. */
const EASE = 0.22;
/* How fast tiles wake up while the pointer moves, and how fast the patch dims once it rests (per second). */
const RISE = 6;
const FALL = 1.6;
/* How fast a tile the pointer has left settles back into the page (per second). */
const SETTLE = 2.6;
/* Speed (px per frame) at which the patch is fully shown. */
const FULL_SPEED = 6;

/* The accent orange, a touch lighter so faint tiles still read on the dark page. */
const TILE = "255, 138, 40";
const SHADOW = "12, 10, 9";

/**
 * Invisible pixel tiles that rise out of the page under a moving cursor.
 *
 * The whole page is paved with tiles nobody sees. Where the pointer moves, the
 * tiles around it lift: they gain colour, float a few pixels up and cast a soft
 * shadow on the spot they came from. Tiles the pointer has passed settle back
 * down on their own, so a trail follows the cursor and fades behind it. Tiles are
 * fixed to the page, not to the screen, so they scroll with the content.
 *
 * Nothing is drawn while nothing moves; the loop stops itself once every tile
 * has settled.
 */
export function CursorAura() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let width = 0;
    let height = 0;

    const pointer = { x: -9999, y: -9999 };
    const at = { x: -9999, y: -9999 };
    // How awake the patch is: rises with movement, falls while the pointer rests.
    let shown = 0;
    let moving = 0;
    // 0 over plain background, 1 over an element marked data-aura.
    let heat = 0;
    let targetHeat = 0;
    let inside = false;

    // How far each tile is raised, keyed by its column and row in document space.
    // A tile leaves the map once it has settled, so the map only ever holds the trail.
    const lifts = new Map<number, number>();
    const keyOf = (col: number, row: number) => row * 100000 + col;

    let frame = 0;
    let running = false;
    let last = performance.now();

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    /** How strongly the pointer pulls a tile up: fully in the middle, nothing at the rim. */
    const pullAt = (x: number, y: number, radius: number) => {
      const r = Math.hypot(x - at.x, y - at.y);
      if (r >= radius) return 0;
      const t = 1 - r / radius;
      return t * t * (3 - 2 * t);
    };

    /** Wakes the tiles around the pointer and lets every other tile settle. */
    const update = (dt: number) => {
      const radius = RADIUS[0] + (RADIUS[1] - RADIUS[0]) * heat;
      const scrollY = window.scrollY;
      const settle = Math.exp(-SETTLE * dt);

      for (const [key, lift] of lifts) {
        const next = lift * settle;
        if (next < 0.004) lifts.delete(key);
        else lifts.set(key, next);
      }

      if (shown < 0.004) return;
      const c0 = Math.floor((at.x - radius) / CELL);
      const c1 = Math.ceil((at.x + radius) / CELL);
      const r0 = Math.floor((at.y + scrollY - radius) / CELL);
      const r1 = Math.ceil((at.y + scrollY + radius) / CELL);
      for (let row = r0; row <= r1; row++) {
        const cy = row * CELL + CELL / 2 - scrollY;
        for (let col = c0; col <= c1; col++) {
          const cx = col * CELL + CELL / 2;
          const target = pullAt(cx, cy, radius) * shown;
          if (target <= 0.01) continue;
          const key = keyOf(col, row);
          const lift = lifts.get(key) ?? 0;
          // Tiles rise quickly toward the pointer and only settle through the decay above.
          if (target > lift) lifts.set(key, lift + (target - lift) * Math.min(1, RISE * dt));
        }
      }
    };

    const draw = () => {
      ctx.clearRect(0, 0, width, height);
      if (lifts.size === 0) return;

      const scrollY = window.scrollY;
      const size = CELL - GAP;

      // Shadows first, so a raised tile never covers its neighbour's shadow oddly.
      for (const [key, lift] of lifts) {
        const col = ((key % 100000) + 100000) % 100000;
        const row = (key - col) / 100000;
        const x = col * CELL + GAP / 2;
        const y = row * CELL + GAP / 2 - scrollY;
        if (y > height || y + CELL < 0 || x > width) continue;
        const k = lift * lift;
        ctx.fillStyle = `rgba(${SHADOW}, ${(TILE_ALPHA * SHADOW_ALPHA * k).toFixed(3)})`;
        ctx.fillRect(x + 1, y + 1 + LIFT * k * 0.4, size, size);
      }

      for (const [key, lift] of lifts) {
        const col = ((key % 100000) + 100000) % 100000;
        const row = (key - col) / 100000;
        const x = col * CELL + GAP / 2;
        const y = row * CELL + GAP / 2 - scrollY;
        if (y > height || y + CELL < 0 || x > width) continue;
        const k = lift * lift;
        const rise = LIFT * k;
        ctx.fillStyle = `rgba(${TILE}, ${(TILE_ALPHA * k).toFixed(3)})`;
        ctx.fillRect(x, y - rise, size, size);
        // A brighter top edge sells the tile as a raised block rather than a flat square.
        ctx.fillStyle = `rgba(255, 210, 160, ${(TILE_ALPHA * 0.5 * k).toFixed(3)})`;
        ctx.fillRect(x, y - rise, size, 1);
      }
    };

    const tick = (now: number) => {
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;

      const px = at.x;
      const py = at.y;
      at.x += (pointer.x - at.x) * EASE;
      at.y += (pointer.y - at.y) * EASE;
      const speed = Math.hypot(at.x - px, at.y - py);
      moving = inside ? Math.min(1, speed / FULL_SPEED) : 0;

      // Wake quickly while the pointer moves, dim slowly once it rests.
      if (moving > shown) shown += (moving - shown) * Math.min(1, RISE * dt);
      else shown += (moving - shown) * Math.min(1, FALL * dt);
      heat += (targetHeat - heat) * 0.1;

      update(dt);
      draw();

      if (lifts.size === 0 && shown < 0.004 && moving === 0) {
        shown = 0;
        ctx.clearRect(0, 0, width, height);
        running = false;
        return;
      }
      frame = requestAnimationFrame(tick);
    };

    const start = () => {
      if (running) return;
      running = true;
      last = performance.now();
      frame = requestAnimationFrame(tick);
    };

    const onPointerMove = (e: PointerEvent) => {
      if (!inside) {
        // First move, or a return to the page: place the patch instead of flying it in.
        at.x = e.clientX;
        at.y = e.clientY;
      }
      inside = true;
      pointer.x = e.clientX;
      pointer.y = e.clientY;
      const el = e.target instanceof Element ? e.target.closest("[data-aura]") : null;
      targetHeat = el ? 1 : 0;
      start();
    };

    const onPointerLeave = () => {
      inside = false;
      targetHeat = 0;
      start();
    };

    // Scrolling slides the tiles under a resting pointer, so it counts as movement too.
    const onScroll = () => {
      if (!inside) return;
      shown = Math.max(shown, 0.6);
      start();
    };

    resize();
    window.addEventListener("resize", resize);
    window.addEventListener("pointermove", onPointerMove, { passive: true });
    window.addEventListener("scroll", onScroll, { passive: true });
    document.addEventListener("pointerleave", onPointerLeave);

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("scroll", onScroll);
      document.removeEventListener("pointerleave", onPointerLeave);
    };
  }, []);

  return (
    <div className={styles.wrap} aria-hidden="true">
      <canvas ref={ref} className={styles.canvas} />
      <div className={styles.vignette} />
    </div>
  );
}
