"use client";

import { useCallback, useEffect, useRef, useState, type CSSProperties } from "react";
import { ChatDemo } from "./ChatDemo";
import { copy } from "./copy";
import { DuckLane } from "./DuckLane";
import { Globe } from "./Globe";
import styles from "./quack.module.css";
import { Reveal } from "./Reveal";
import { TempoDucks } from "./TempoDucks";
import { UniCarousel } from "./UniCarousel";
import { useRotator } from "./useRotator";
import { useScrollGrow } from "./useScrollGrow";

/** How long a tab stays open before the section moves on by itself. */
const TAB_MS = 8000;

/** How small the middle block starts before it grows into place. */
const GROW_FROM = 0.78;

const TABS = [copy.quack.tabs.uni, copy.quack.tabs.chat, copy.quack.tabs.tempo];

/**
 * "Quack?" — the three things the product does, with a globe on the left and a
 * lane of ducks down the right.
 *
 * The first tab is open on arrival, so scrolling down already shows something
 * playing. Pointing at another item slides the rounded highlight onto it and
 * swaps the panel; leaving the list hands control back to the timer.
 */
export function QuackSection() {
  const ref = useRef<HTMLElement>(null);
  const growRef = useScrollGrow(GROW_FROM, 1);
  const [onScreen, setOnScreen] = useState(false);
  const [hovering, setHovering] = useState(false);
  const [tab, setTab] = useRotator(TABS.length, TAB_MS, hovering || !onScreen);
  // Set when a pin on the globe is clicked, so the carousel jumps to that program.
  const [focusId, setFocusId] = useState<string | null>(null);

  // Nothing animates while the section is scrolled away.
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver((entries) => setOnScreen(entries.some((e) => e.isIntersecting)), {
      threshold: 0.2,
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const handlePickProgram = useCallback(
    (id: string) => {
      setTab(0);
      setFocusId(id);
    },
    [setTab]
  );

  return (
    <section ref={ref} className={styles.section} id="quack" aria-labelledby="quack-heading">
      <Reveal>
        <h2 id="quack-heading" className={styles.heading}>
          {copy.quack.heading}
        </h2>
      </Reveal>

      <div className={styles.stage}>
        <Reveal className={styles.globeWrap} from="left" delay={0.05}>
          <Globe onPickProgram={handlePickProgram} />
        </Reveal>

        <div ref={growRef} className={styles.mainWrap}>
          <div className={styles.main}>
            <Reveal className={styles.tabsWrap} delay={0.1}>
              <div
                className={styles.tabs}
                role="tablist"
                aria-orientation="vertical"
                aria-label={copy.quack.heading}
                style={{ "--i": tab } as CSSProperties}
                onMouseEnter={() => setHovering(true)}
                onMouseLeave={() => setHovering(false)}
              >
                <span className={styles.indicator} aria-hidden="true" />

                {TABS.map((label, i) => (
                  <button
                    key={label}
                    type="button"
                    role="tab"
                    id={`quack-tab-${i}`}
                    aria-selected={i === tab}
                    aria-controls={`quack-panel-${i}`}
                    tabIndex={i === tab ? 0 : -1}
                    className={styles.tab}
                    data-active={i === tab}
                    data-aura
                    onMouseEnter={() => setTab(i)}
                    onFocus={() => setTab(i)}
                    onClick={() => setTab(i)}
                  >
                    <span className={styles.tabNum}>{i + 1}.</span>
                    {label}
                  </button>
                ))}
              </div>
            </Reveal>

            <Reveal className={styles.panelWrap} from="right" delay={0.18}>
              <div className={styles.panel} data-aura>
                {/* Panels stay mounted so they cross-fade; `inert` keeps the hidden ones
                    out of the tab order and the accessibility tree. */}
                {TABS.map((label, i) => (
                  <div
                    key={label}
                    id={`quack-panel-${i}`}
                    role="tabpanel"
                    aria-labelledby={`quack-tab-${i}`}
                    className={styles.panelView}
                    data-active={i === tab}
                    inert={i !== tab}
                  >
                    {i === 0 && <UniCarousel active={tab === 0 && onScreen} focusId={focusId} />}
                    {i === 1 && <ChatDemo active={tab === 1 && onScreen} />}
                    {i === 2 && <TempoDucks />}
                  </div>
                ))}
              </div>
            </Reveal>
          </div>
        </div>
      </div>

      <DuckLane active={onScreen} />
    </section>
  );
}
