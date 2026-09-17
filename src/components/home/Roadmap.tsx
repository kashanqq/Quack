"use client";

import { useEffect, useLayoutEffect, useRef, useState, type CSSProperties } from "react";
import styles from "./roadmap.module.css";

/* Journey from product-logic.md: profile -> program picks -> roadmap -> study sets -> exam day.
   `y` offsets make the path zigzag instead of running in a straight line. */
const STEPS = [
  { name: "Profile", y: 22 },
  { name: "Programs", y: -34 },
  { name: "Roadmap", y: 30 },
  { name: "Sets", y: -26 },
  { name: "Exam day", y: 18 },
];

const STAGE_MS = 1800;
const START_MS = 300;

type StepState = "pending" | "active" | "done";

/**
 * Intro animation (~9.3s): nodes appear one at a time, the group slides left to stay centred,
 * lines grow between nodes and dots go grey -> yellow -> green.
 */
export function Roadmap() {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(STEPS.length);
  const [allDone, setAllDone] = useState(true);
  const [noAnim, setNoAnim] = useState(true);

  // Before first paint: reset to the empty state without animating away from the full one.
  useLayoutEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    setVisible(0);
    setAllDone(false);
  }, []);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const frame = requestAnimationFrame(() => setNoAnim(false));
    const timers: ReturnType<typeof setTimeout>[] = [];

    const play = () => {
      STEPS.forEach((_, i) => timers.push(setTimeout(() => setVisible(i + 1), START_MS + i * STAGE_MS)));
      timers.push(setTimeout(() => setAllDone(true), START_MS + STEPS.length * STAGE_MS));
    };

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          observer.disconnect();
          play();
        }
      },
      { threshold: 0.5 }
    );
    if (ref.current) observer.observe(ref.current);

    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      timers.forEach(clearTimeout);
    };
  }, []);

  return (
    <div ref={ref} className={`${styles.roadmap} ${noAnim ? styles.noAnim : ""}`} role="list" aria-label="Roadmap stages">
      {STEPS.map((step, i) => {
        const shown = i < visible;
        const age = visible - 1 - i;
        const state: StepState = allDone || age >= 2 ? "done" : age === 1 ? "active" : "pending";
        const next = STEPS[i + 1];
        const isLast = !next;

        // Hidden nodes wait at the spot they will occupy when revealed, so they fade in without sliding.
        const pos = shown ? i - (visible - 1) / 2 : i / 2;
        const style = {
          "--pos": pos,
          "--y": step.y,
          ...(next ? { "--y-next": next.y } : {}),
        } as CSSProperties;

        return (
          <div
            key={step.name}
            role="listitem"
            data-state={state}
            style={style}
            className={[styles.step, shown && styles.visible, i + 1 < visible && styles.hasLine].filter(Boolean).join(" ")}
          >
            {!isLast && <img className={styles.stepLine} src="/assets/line.svg" alt="" />}
            <img className={styles.stepNode} src={i === 0 ? "/assets/node-start.svg" : "/assets/node.svg"} alt="" />
            <span className={styles.stepLabel}>
              {step.name}
              <span className={styles.stepDot}>
                <img className={`${styles.dot} ${styles.dotPending}`} src="/assets/dot-white.svg" alt="" />
                <img className={`${styles.dot} ${styles.dotActive}`} src="/assets/dot-yellow.svg" alt="" />
                <img className={`${styles.dot} ${styles.dotDone}`} src="/assets/dot-green.svg" alt="" />
              </span>
            </span>
          </div>
        );
      })}
    </div>
  );
}
