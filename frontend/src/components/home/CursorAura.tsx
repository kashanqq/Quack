"use client";

import { useEffect, useRef } from "react";
import styles from "./aura.module.css";

/* Aura size in CSS pixels, at rest and while the pointer is on something interactive. */
const RADIUS_IDLE = 190;
const RADIUS_HOT = 310;
/* Peak opacity of the warm glow at its centre. */
const ALPHA_IDLE = 0.1;
const ALPHA_HOT = 0.17;
/* Pointer easing per frame — the aura trails the cursor instead of snapping to it. */
const EASE = 0.14;

const GLOW = "255, 122, 0";
const NOISE_TILE = 128;

/**
 * A warm, grainy aura that follows the cursor.
 *
 * It lives behind every section, so when the pointer reaches something
 * interactive the grain shows up *behind* that element and lights it from below.
 * Elements opt into the stronger version with `data-aura`.
 *
 * Nothing is drawn until the pointer moves, and the loop shuts itself off once
 * the aura has faded, so an idle page costs no frames.
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

    let targetX = -9999;
    let targetY = -9999;
    let currentX = -9999;
    let currentY = -9999;
    // 0 while the pointer is away, 1 while it is over the page.
    let presence = 0;
    let targetPresence = 0;
    // 0 over plain background, 1 over an element marked data-aura.
    let heat = 0;
    let targetHeat = 0;

    let frame = 0;
    let running = false;

    // One tile of static grain, reused every frame and offset to make it shimmer.
    const tile = document.createElement("canvas");
    tile.width = NOISE_TILE;
    tile.height = NOISE_TILE;
    const tileCtx = tile.getContext("2d");
    if (!tileCtx) return;
    const grain = tileCtx.createImageData(NOISE_TILE, NOISE_TILE);
    for (let i = 0; i < grain.data.length; i += 4) {
      const v = Math.random();
      grain.data[i] = 255;
      grain.data[i + 1] = 235;
      grain.data[i + 2] = 215;
      // Sparse: only the brightest samples show, so it reads as grain, not fog.
      grain.data[i + 3] = v > 0.72 ? Math.round((v - 0.72) * 620) : 0;
    }
    tileCtx.putImageData(grain, 0, 0);
    const noise = ctx.createPattern(tile, "repeat");

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

    const draw = () => {
      ctx.clearRect(0, 0, width, height);
      if (presence < 0.004) return;

      const radius = RADIUS_IDLE + (RADIUS_HOT - RADIUS_IDLE) * heat;
      const alpha = (ALPHA_IDLE + (ALPHA_HOT - ALPHA_IDLE) * heat) * presence;

      const glow = ctx.createRadialGradient(currentX, currentY, 0, currentX, currentY, radius);
      glow.addColorStop(0, `rgba(${GLOW}, ${alpha})`);
      glow.addColorStop(0.45, `rgba(${GLOW}, ${alpha * 0.35})`);
      glow.addColorStop(1, `rgba(${GLOW}, 0)`);
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(currentX, currentY, radius, 0, Math.PI * 2);
      ctx.fill();

      if (!noise) return;
      // `source-atop` keeps the grain inside what the glow already painted, so the
      // noise fades out exactly where the aura does.
      ctx.save();
      ctx.globalCompositeOperation = "source-atop";
      ctx.globalAlpha = (0.32 + 0.38 * heat) * presence;
      ctx.translate(Math.random() * NOISE_TILE, Math.random() * NOISE_TILE);
      ctx.fillStyle = noise;
      ctx.fillRect(-NOISE_TILE, -NOISE_TILE, width + NOISE_TILE * 2, height + NOISE_TILE * 2);
      ctx.restore();
    };

    const tick = () => {
      currentX += (targetX - currentX) * EASE;
      currentY += (targetY - currentY) * EASE;
      presence += (targetPresence - presence) * EASE;
      heat += (targetHeat - heat) * EASE;

      draw();

      const settled =
        Math.abs(targetX - currentX) < 0.4 &&
        Math.abs(targetY - currentY) < 0.4 &&
        Math.abs(targetPresence - presence) < 0.004 &&
        Math.abs(targetHeat - heat) < 0.004;

      if (settled && targetPresence === 0) {
        presence = 0;
        draw();
        running = false;
        return;
      }
      frame = requestAnimationFrame(tick);
    };

    const start = () => {
      if (running) return;
      running = true;
      frame = requestAnimationFrame(tick);
    };

    const onPointerMove = (e: PointerEvent) => {
      if (targetPresence === 0) {
        // First move, or a return to the page: place the aura instead of flying it in.
        currentX = e.clientX;
        currentY = e.clientY;
      }
      targetX = e.clientX;
      targetY = e.clientY;
      targetPresence = 1;
      const el = e.target instanceof Element ? e.target.closest("[data-aura]") : null;
      targetHeat = el ? 1 : 0;
      start();
    };

    const onPointerLeave = () => {
      targetPresence = 0;
      targetHeat = 0;
      start();
    };

    resize();
    window.addEventListener("resize", resize);
    window.addEventListener("pointermove", onPointerMove, { passive: true });
    document.addEventListener("pointerleave", onPointerLeave);

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", onPointerMove);
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
