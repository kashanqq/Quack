"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";
import { copy } from "./copy";
import styles from "./layers.module.css";

const LAYERS = copy.layers.items;
const N = LAYERS.length;
/** Where each layer sits down the stack, in gaps. */
const slot = (i: number) => i;

/**
 * "Что внутри": the six layers Quack! is built from, stacked close together on
 * one screen, each bobbing gently on its own beat.
 *
 * Pointing at a layer (or tapping it on a touch screen) brings it forward and a
 * little larger, blurs the rest, and shows its description beside it —
 * alternating sides, the way the stack was first drawn. The layers themselves
 * overlap, so each one is picked through an invisible band level with it.
 */
export function LayerStack() {
  const sectionRef = useRef<HTMLElement>(null);
  const [active, setActive] = useState<number | null>(null);
  const t = copy.layers;

  // A tap outside the stack puts a picked layer back.
  useEffect(() => {
    if (active === null) return;
    const onDown = (e: PointerEvent) => {
      if (!sectionRef.current?.contains(e.target as Node)) setActive(null);
    };
    document.addEventListener("pointerdown", onDown);
    return () => document.removeEventListener("pointerdown", onDown);
  }, [active]);

  return (
    <section ref={sectionRef} id="how-it-works" className={styles.section} aria-labelledby="layers-heading">
      <header className={styles.head}>
        <h2 id="layers-heading" className={styles.heading}>
          {t.heading}
        </h2>
        <p className={styles.lead}>{t.lead}</p>
        <p className={styles.hint}>{t.hint}</p>
      </header>

      <div className={styles.wrap} data-picked={active !== null} onMouseLeave={() => setActive(null)}>
        <div className={styles.stack}>
          {LAYERS.map((layer, i) => (
            <div
              key={layer.name}
              className={styles.layer}
              data-active={i === active}
              style={{ "--i": i, "--y": slot(i), zIndex: i === active ? 50 : N - i } as CSSProperties}
              aria-hidden="true"
            >
              <div className={styles.bob}>
                {/* eslint-disable-next-line @next/next/no-img-element -- a plain cut-out, sized by CSS */}
                <img src={`/assets/layers/layer-${i + 1}.webp`} alt="" draggable={false} />
              </div>
            </div>
          ))}

          {LAYERS.map((layer, i) => (
            <button
              key={layer.name}
              type="button"
              className={styles.band}
              // Each band runs from halfway to the layer above to halfway to the one below.
              style={{ "--from": i && (slot(i - 1) + slot(i)) / 2, "--to": (slot(i) + slot(i + 1)) / 2 } as CSSProperties}
              aria-label={layer.name}
              aria-expanded={i === active}
              aria-controls={`layer-card-${i}`}
              onMouseEnter={() => setActive(i)}
              onFocus={() => setActive(i)}
              onClick={(e) => {
                // A mouse already picked it on hover; a tap toggles.
                if (e.nativeEvent instanceof PointerEvent && e.nativeEvent.pointerType === "mouse") return;
                setActive((a) => (a === i ? null : i));
              }}
            />
          ))}
        </div>

        <div className={styles.cards}>
          {LAYERS.map((layer, i) => (
            <article
              key={layer.name}
              id={`layer-card-${i}`}
              className={styles.card}
              style={{ "--i": i, "--y": slot(i) } as CSSProperties}
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
      </div>
    </section>
  );
}
