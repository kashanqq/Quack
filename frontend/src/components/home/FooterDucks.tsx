"use client";

import { useEffect, useRef, useState } from "react";
import { SCENE_PALETTE } from "./HeroLandscape";
import { PixelDuck } from "@/components/duck/PixelDuck";
import { PixelSprite } from "./PixelSprite";
import styles from "./footer.module.css";

const UNIT = 3;

const POND = [
  "..wwwwwwwwwwwwwwwwwwwwwwwwwwww..",
  ".wwwwwwwwwwwwwwwwwwwwwwwwwwwwww.",
  "...wwwwwwwwwwwwwwwwwwwwwwwwww...",
];

const TUFT = [
  "..t....t.t..",
  "gggGgggggGgg",
];

/** How long a wave lasts each time the footer comes into view. */
const WAVE_MS = 3200;

/**
 * Two ducks on the top edge of the footer: one asleep in a small pond, one that
 * waves goodbye whenever the reader reaches the end of the page.
 */
export function FooterDucks() {
  const ref = useRef<HTMLDivElement>(null);
  const [waving, setWaving] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let timer: ReturnType<typeof setTimeout>;
    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries.some((e) => e.isIntersecting)) return;
        setWaving(true);
        clearTimeout(timer);
        timer = setTimeout(() => setWaving(false), WAVE_MS);
      },
      { threshold: 1 }
    );
    observer.observe(el);
    return () => {
      clearTimeout(timer);
      observer.disconnect();
    };
  }, []);

  return (
    <div ref={ref} className={styles.ducks} aria-hidden="true">
      <div className={styles.waver}>
        <PixelSprite className={styles.tuft} map={TUFT} palette={SCENE_PALETTE} unit={UNIT} />
        <div className={styles.waverDuck}>
          <PixelDuck tempo="steady" waving={waving} />
        </div>
      </div>

      <div className={styles.pond}>
        <PixelSprite map={POND} palette={SCENE_PALETTE} unit={UNIT} />
        <div className={styles.sleep}>
          <div className={styles.sleeper}>
            <PixelDuck tempo="chill" asleep />
          </div>
        </div>
        <span className={styles.zzz}>
          <i>z</i>
          <i>z</i>
          <i>z</i>
        </span>
      </div>
    </div>
  );
}
