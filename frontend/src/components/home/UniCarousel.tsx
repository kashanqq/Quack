"use client";

import { PROGRAMS, type Program } from "@/components/choice/programs";
import { copy } from "./copy";
import styles from "./quack.module.css";
import { useRotator } from "./useRotator";

/** Seconds one card stays on screen before the next one takes over. */
const CARD_S = 5;

/** Short, gender-neutral traits pulled from the program data. */
function fitsOf(p: Program): string[] {
  const bits = [
    p.warm ? "тёплый климат" : "северный климат",
    p.megacity ? "большой город" : "спокойный город",
    p.englishTaught ? "обучение на английском" : `язык: ${p.language}`,
    p.research === "сильная" ? "сильная наука" : "практика важнее науки",
  ];
  return bits.slice(0, 3);
}

function admissionOf(p: Program): string {
  const parts = [`IELTS от ${p.ieltsMin.toFixed(1)}`];
  if (p.satMin) parts.push(`SAT от ${p.satMin}`);
  return parts.join(" · ");
}

type UniCarouselProps = {
  /** True while this is the open tab — the carousel only runs when it is visible. */
  active: boolean;
};

/**
 * Cycles through demo programs, one every five seconds. Every card stays mounted
 * and cross-fades, so a card leaves while the next one is already arriving.
 */
export function UniCarousel({ active }: UniCarouselProps) {
  const [index, setIndex] = useRotator(PROGRAMS.length, CARD_S * 1000, !active);
  const t = copy.quack.uni;

  return (
    <div className={styles.uni}>
      <div className={styles.uniHead}>
        <span className={styles.uniCaption}>{t.caption}</span>
        <span className={styles.demoBadge}>{t.demo}</span>
      </div>

      <div className={styles.uniStack}>
        {PROGRAMS.map((p, i) => (
          <article key={p.id} className={styles.uniCard} data-active={i === index} aria-hidden={i !== index}>
            <h3 className={styles.uniName}>{p.university}</h3>
            <p className={styles.uniProgram}>{p.program}</p>
            <p className={styles.uniPlace}>
              {p.city}, {p.country}
            </p>

            <dl className={styles.uniFacts}>
              <div>
                <dt>{t.admission}</dt>
                <dd>{admissionOf(p)}</dd>
              </div>
              <div>
                <dt>{t.cost}</dt>
                <dd>
                  €{p.costEur.toLocaleString("ru-RU")}
                  {t.perYear}
                </dd>
              </div>
              <div>
                <dt>{t.deadline}</dt>
                <dd>{p.deadline}</dd>
              </div>
            </dl>

            <p className={styles.uniFits}>
              <span className={styles.uniFitsLabel}>{t.fits}</span>
              {fitsOf(p).map((bit) => (
                <span key={bit} className={styles.uniTag}>
                  {bit}
                </span>
              ))}
            </p>
          </article>
        ))}
      </div>

      <div className={styles.dots} role="group" aria-label={t.caption}>
        {PROGRAMS.map((p, i) => (
          <button
            key={p.id}
            type="button"
            aria-label={p.university}
            aria-current={i === index}
            className={styles.dot}
            data-active={i === index}
            onClick={() => setIndex(i)}
          >
            {/* Restarts on every change, so the fill always tracks the live card. */}
            {i === index && (
              <span
                key={`${index}-${active}`}
                className={styles.dotFill}
                style={{ animationDuration: active ? `${CARD_S}s` : "0s" }}
              />
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
