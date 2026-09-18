"use client";

import { useEffect, useRef } from "react";

/**
 * Drives a `--grow` custom property from `from` to `to` as the element rises
 * through the viewport, so a block can swell as you scroll down to it.
 *
 * The value is written straight onto the node: scrolling must not re-render React.
 * Put the ref on a wrapper and the transform on a child — a transform does not
 * change the wrapper's own box, so the measurement never feeds back on itself.
 */
export function useScrollGrow(from: number, to: number) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      el.style.setProperty("--grow", String(to));
      return;
    }

    let frame = 0;

    const update = () => {
      frame = 0;
      const rect = el.getBoundingClientRect();
      const vh = window.innerHeight;
      // 0 while the block's top is still at the bottom edge, 1 once it has
      // climbed to roughly a third of the way up the screen.
      const start = vh;
      const end = vh * 0.3;
      const p = Math.max(0, Math.min(1, (start - rect.top) / (start - end)));
      el.style.setProperty("--grow", (from + (to - from) * p).toFixed(4));
    };

    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };

    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, [from, to]);

  return ref;
}
