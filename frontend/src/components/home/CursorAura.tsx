"use client";

import { useEffect, useRef } from "react";
import styles from "./aura.module.css";

/* Grid cell in CSS pixels, and how finely each line is sampled so it can bend. */
const CELL = 44;
const SAMPLES_PER_CELL = 4;
/* Radius of the visible patch around the pointer, at rest and over something interactive. */
const RADIUS = [240, 300];
/* How deep the dent is: the share of the way a point is pulled toward the pointer. */
const DEPTH = 0.42;
/* Peak line opacity in the middle of the patch. */
const LINE_ALPHA = 0.3;
/* Pointer easing per frame — the dent trails the cursor instead of snapping to it. */
const EASE = 0.2;
/* How fast the grid shows up while moving and fades once the pointer rests (per second). */
const RISE = 5;
const FALL = 1.4;
/* Speed (px per frame) at which the grid is fully shown. */
const FULL_SPEED = 6;

const LINE = "255, 236, 218";
const WARM = "255, 122, 0";

/**
 * An invisible grid that shows itself only around a moving cursor.
 *
 * The page carries a grid nobody sees. Where the pointer moves, a round patch
 * of it lights up and sags into the page — lines near the pointer are pulled
 * toward it, as if the surface were pressed in from the viewer's side. When the
 * pointer rests the patch fades away again. The grid is fixed to the page, not
 * to the screen, so it scrolls with the content.
 *
 * Nothing is drawn while nothing moves; the loop stops itself once the patch
 * has faded.
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
    // How visible the patch is: rises with movement, falls while the pointer rests.
    let shown = 0;
    let moving = 0;
    // 0 over plain background, 1 over an element marked data-aura.
    let heat = 0;
    let targetHeat = 0;
    let inside = false;

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

    /**
     * Where a grid point ends up, and how strongly its line shows there. Points
     * inside the patch are pulled toward the centre, most at mid-radius, none at
     * the centre or the rim, so the grid stays continuous.
     */
    const bend = (x: number, y: number, radius: number) => {
      const dx = x - at.x;
      const dy = y - at.y;
      const r = Math.hypot(dx, dy);
      if (r >= radius) return { x, y, a: 0 };
      const t = 1 - r / radius;
      const pull = DEPTH * t * t;
      const fade = t * t * (3 - 2 * t);
      return { x: x - dx * pull, y: y - dy * pull, a: fade };
    };

    const draw = () => {
      ctx.clearRect(0, 0, width, height);
      if (shown < 0.004) return;

      const radius = RADIUS[0] + (RADIUS[1] - RADIUS[0]) * heat;
      const alpha = LINE_ALPHA * shown;
      // The grid is anchored to the document, so it scrolls with the page.
      const offY = -(window.scrollY % CELL);
      const step = CELL / SAMPLES_PER_CELL;
      const x0 = Math.floor((at.x - radius) / CELL) * CELL;
      const x1 = at.x + radius;
      const y0 = Math.floor((at.y - radius - offY) / CELL) * CELL + offY;
      const y1 = at.y + radius;

      ctx.lineWidth = 1;
      ctx.lineCap = "round";

      const stroke = (ax: number, ay: number, bx: number, by: number) => {
        const a = bend(ax, ay, radius);
        const b = bend(bx, by, radius);
        const k = Math.min(a.a, b.a);
        if (k <= 0.01) return;
        ctx.strokeStyle = `rgba(${LINE}, ${(alpha * k).toFixed(3)})`;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      };

      for (let x = x0; x <= x1; x += CELL) {
        for (let y = y0; y < y1; y += step) stroke(x, y, x, y + step);
      }
      for (let y = y0; y <= y1; y += CELL) {
        for (let x = x0; x < x1; x += step) stroke(x, y, x + step, y);
      }

      // A faint warm shadow in the bottom of the dent gives it depth.
      const g = ctx.createRadialGradient(at.x, at.y, 0, at.x, at.y, radius * 0.6);
      g.addColorStop(0, `rgba(${WARM}, ${0.07 * shown})`);
      g.addColorStop(1, `rgba(${WARM}, 0)`);
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(at.x, at.y, radius * 0.6, 0, Math.PI * 2);
      ctx.fill();
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

      // Show quickly while the pointer moves, fade slowly once it rests.
      if (moving > shown) shown += (moving - shown) * Math.min(1, RISE * dt);
      else shown += (moving - shown) * Math.min(1, FALL * dt);
      heat += (targetHeat - heat) * 0.1;

      draw();

      if (shown < 0.004 && moving === 0) {
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
        // First move, or a return to the page: place the dent instead of flying it in.
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

    // Scrolling moves the grid under a resting pointer, so it counts as movement too.
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
