"use client";

import { useEffect, useRef, useState } from "react";
import { copy } from "./copy";
import styles from "./layers.module.css";

const LAYERS = copy.layers.items;
const N = LAYERS.length;

/** Scroll distance spent on each layer, in viewport heights: two or three wheel notches. */
const PER_LAYER_VH = 0.4;
/** Once the scroll has been still this long, the nearest layer is brought fully into focus. */
const SNAP_IDLE_MS = 140;
/** How far apart neighbouring layers sit, as a share of the layer width. */
const GAP = 0.36;
/** Extra room the neighbours make for the one in focus, as a share of the width. */
const SPREAD = 0.2;
/** Size of the layer in focus relative to the rest. Images are laid out at the focused
    size and only ever scaled down, so the one in focus is drawn at full resolution. */
const FOCUS_SCALE = 1.3;
/** Blur and dimming of a layer one step away from focus; further ones get no worse. */
const BLUR_PX = 5;
const DIM = 0.45;

/**
 * "Под основой": the six layers Quack! is built from, one on top of the other.
 *
 * The section is several screens tall and its stage is sticky, so scrolling
 * moves a focus down the stack instead of moving the page. The layer in focus
 * grows and sharpens with its description beside it; the neighbours step
 * aside, blurred. Positions are written straight to the DOM every frame, so
 * scrolling never re-renders React — only the focused index is state.
 */
export function LayerStack() {
  const sectionRef = useRef<HTMLElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const layerRefs = useRef<(HTMLDivElement | null)[]>([]);
  const [active, setActive] = useState(0);
  const t = copy.layers;

  useEffect(() => {
    const section = sectionRef.current;
    const stage = stageRef.current;
    if (!section || !stage) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let frame = 0;
    let target = 0;
    let pos = 0;
    let last = -1;

    const place = () => {
      // The rendered width is the focused one; spacing is measured on the resting size.
      const w = (layerRefs.current[0]?.offsetWidth ?? 0) / FOCUS_SCALE;
      for (let i = 0; i < N; i++) {
        const el = layerRefs.current[i];
        if (!el) continue;
        const d = i - pos;
        const near = Math.max(0, 1 - Math.abs(d));
        const away = Math.min(Math.abs(d), 1);
        // The focused layer sits in the middle; the rest queue above and below it,
        // pushed a little further out so the big one has room.
        const y = d * GAP * w + Math.max(-1, Math.min(1, d)) * SPREAD * w;
        const scale = (1 + (FOCUS_SCALE - 1) * near) / FOCUS_SCALE;
        el.style.transform = `translate(-50%, -50%) translateY(${y.toFixed(1)}px) scale(${scale.toFixed(3)})`;
        el.style.filter = reduced ? "" : `blur(${(away * BLUR_PX).toFixed(2)}px)`;
        el.style.opacity = (1 - away * DIM).toFixed(3);
        // Upper layers cover lower ones, as in a real stack, but the focused one always wins.
        el.style.zIndex = String(near > 0.5 ? 50 : N - i);
      }
    };

    const tick = () => {
      pos += (target - pos) * (reduced ? 1 : 0.14);
      if (Math.abs(target - pos) < 0.001) pos = target;
      place();
      const idx = Math.round(pos);
      if (idx !== last) {
        last = idx;
        setActive(idx);
      }
      frame = pos === target ? 0 : requestAnimationFrame(tick);
    };

    // Where the page has to be for layer i to be exactly in focus.
    const scrollFor = (i: number) => {
      const run = section.offsetHeight - window.innerHeight;
      return section.getBoundingClientRect().top + window.scrollY + (run * i) / (N - 1);
    };

    // After the wheel stops, finish the move onto the nearest layer, so nobody has
    // to nudge the page into place by hand.
    let idle = 0;
    const snap = () => {
      const rect = section.getBoundingClientRect();
      const run = rect.height - window.innerHeight;
      const raw = run > 0 ? -rect.top / run : -1;
      // Only while the stage is pinned; entering and leaving the section scroll freely.
      if (raw <= 0 || raw >= 1) return;
      const top = scrollFor(Math.round(raw * (N - 1)));
      if (Math.abs(top - window.scrollY) > 2) window.scrollTo({ top, behavior: reduced ? "auto" : "smooth" });
    };

    const onScroll = () => {
      const rect = section.getBoundingClientRect();
      const run = rect.height - window.innerHeight;
      const p = run > 0 ? Math.max(0, Math.min(1, -rect.top / run)) : 0;
      target = p * (N - 1);
      if (!frame) frame = requestAnimationFrame(tick);
      clearTimeout(idle);
      idle = window.setTimeout(snap, SNAP_IDLE_MS);
    };

    onScroll();
    pos = target;
    place();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      cancelAnimationFrame(frame);
      clearTimeout(idle);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, []);

  /** Scrolls the page so that layer `i` is the one in focus. */
  const jumpTo = (i: number) => {
    const section = sectionRef.current;
    if (!section) return;
    const run = section.offsetHeight - window.innerHeight;
    const top = section.getBoundingClientRect().top + window.scrollY + (run * i) / (N - 1);
    window.scrollTo({ top, behavior: "smooth" });
  };

  return (
    <section
      ref={sectionRef}
      id="how-it-works"
      className={styles.section}
      style={{ height: `${100 + PER_LAYER_VH * 100 * (N - 1)}vh` }}
      aria-labelledby="layers-heading"
    >
      <div ref={stageRef} className={styles.stage}>
        <header className={styles.head}>
          <h2 id="layers-heading" className={styles.heading}>
            {t.heading}
          </h2>
          <p className={styles.lead}>{t.lead}</p>
        </header>

        {/* The index along the bottom doubles as navigation. */}
        <ol className={styles.rail}>
          {LAYERS.map((layer, i) => (
            <li key={layer.name}>
              <button
                type="button"
                className={styles.railItem}
                data-active={i === active}
                aria-current={i === active}
                onClick={() => jumpTo(i)}
                data-aura
              >
                <span className={styles.railNum}>L{i + 1}</span>
                {layer.name}
              </button>
            </li>
          ))}
        </ol>

        <div className={styles.stack} aria-hidden="true">
          {LAYERS.map((layer, i) => (
            <div
              key={layer.name}
              ref={(el) => {
                layerRefs.current[i] = el;
              }}
              className={styles.layer}
            >
              <img src={`/assets/layers/layer-${i + 1}.webp`} alt="" draggable={false} />
            </div>
          ))}
        </div>

        {/* Descriptions alternate sides, the way the stack was first drawn. */}
        {LAYERS.map((layer, i) => (
          <article
            key={layer.name}
            className={styles.card}
            data-side={i % 2 === 0 ? "left" : "right"}
            data-active={i === active}
            aria-hidden={i !== active}
          >
            <p className={styles.cardNum}>
              L{i + 1} <span>/ {N}</span>
            </p>
            <h3 className={styles.cardTitle}>{layer.name}</h3>
            <p className={styles.cardTagline}>{layer.tagline}</p>
            <p className={styles.cardText}>{layer.text}</p>
            {layer.tags && (
              <ul className={styles.tags}>
                {layer.tags.map((tag) => (
                  <li key={tag}>{tag}</li>
                ))}
              </ul>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
