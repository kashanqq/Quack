"use client";

import { useState } from "react";
import { copy } from "./copy";
import styles from "./pricing.module.css";

type Billing = "monthly" | "yearly";

/** The plans side by side, with a monthly / yearly switch above them. */
export function PricingPlans() {
  const t = copy.pricing;
  const [billing, setBilling] = useState<Billing>("monthly");

  return (
    <>
      <div className={styles.billing}>
        <div className={styles.switch} role="radiogroup" aria-label={t.heading} data-billing={billing}>
          <span className={styles.switchPill} aria-hidden="true" />
          {(["monthly", "yearly"] as const).map((b) => (
            <button
              key={b}
              type="button"
              role="radio"
              aria-checked={billing === b}
              className={styles.switchItem}
              data-active={billing === b}
              onClick={() => setBilling(b)}
            >
              {t[b]}
            </button>
          ))}
        </div>
        <span className={styles.saving}>{t.yearlyNote}</span>
      </div>

      <div className={styles.plans}>
        {t.plans.map((plan) => {
          const price = plan[billing];
          return (
            <article
              key={plan.id}
              className={styles.plan}
              data-recommended={Boolean(plan.recommended)}
              data-aura
            >
              <p className={styles.badge}>{plan.recommended ? t.recommended : " "}</p>
              <h2 className={styles.planName}>
                Quack<span className={styles.accent}>!</span> {plan.name}
              </h2>
              <p className={styles.blurb}>{plan.blurb}</p>

              <p className={styles.price}>
                {/* Keyed so the number fades in anew whenever the billing changes. */}
                <span key={`${plan.id}-${billing}`} className={styles.amount}>
                  {price.toLocaleString("ru-RU")}
                </span>
                <span className={styles.unit}>{t.perMonth}</span>
              </p>
              <p className={styles.billedNote}>{billing === "yearly" && price > 0 ? t.billedYearly : " "}</p>

              <a className={styles.cta} href="#signup">
                {plan.cta}
              </a>

              <p className={styles.featuresTitle}>{t.featuresTitle}</p>
              <ul className={styles.features}>
                {plan.features.map((f) => (
                  <li key={f}>
                    <span className={styles.check} aria-hidden="true" />
                    {f}
                  </li>
                ))}
              </ul>
            </article>
          );
        })}
      </div>
    </>
  );
}
