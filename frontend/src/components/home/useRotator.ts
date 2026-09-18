"use client";

import { useEffect, useState } from "react";

/**
 * Cycles an index 0..count-1 on a timer. Rotation stops while `paused` is true
 * (pointer on the list, panel not on screen) and never runs for reduced motion.
 */
export function useRotator(count: number, intervalMs: number, paused = false) {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (paused || count < 2) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const id = setInterval(() => setIndex((i) => (i + 1) % count), intervalMs);
    return () => clearInterval(id);
  }, [count, intervalMs, paused]);

  return [index, setIndex] as const;
}
