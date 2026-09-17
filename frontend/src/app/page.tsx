import { copy } from "@/components/home/copy";
import { CursorAura } from "@/components/home/CursorAura";
import { QuackSection } from "@/components/home/QuackSection";
import { Roadmap } from "@/components/home/Roadmap";
import { SiteHeader } from "@/components/home/SiteHeader";
import styles from "@/components/home/home.module.css";
import { TransitionLink } from "@/components/transition/TransitionLink";

export default function HomePage() {
  const t = copy.hero;

  return (
    <div className={styles.page}>
      {/* Fixed behind everything: the aura trails the cursor under the content. */}
      <CursorAura />

      <div className={styles.content}>
        <SiteHeader />

        <main className={styles.hero}>
          <h1 className={styles.title}>
            Quack<span className={styles.accent}>!</span>
          </h1>

          <Roadmap />

          <TransitionLink className={styles.cta} href="/choice" data-aura>
            {t.cta}
          </TransitionLink>

          <p className={styles.subtitle}>
            {t.subtitleBefore}
            <span className={styles.accentSoft}>{t.subtitleAccent}</span>
            {t.subtitleAfter}
          </p>

          <span className={styles.scrollHint} aria-hidden="true">
            {t.scrollHint}
            <i className={styles.scrollArrow} />
          </span>
        </main>

        <QuackSection />
      </div>
    </div>
  );
}
