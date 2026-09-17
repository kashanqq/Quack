import { Roadmap } from "@/components/home/Roadmap";
import { SiteHeader } from "@/components/home/SiteHeader";
import styles from "@/components/home/home.module.css";
import { TransitionLink } from "@/components/transition/TransitionLink";

export default function HomePage() {
  return (
    <div className={styles.page} lang="en">
      <SiteHeader />

      <main className={styles.hero}>
        <h1 className={styles.title}>
          Quack<span className={styles.accent}>!</span>
        </h1>
        <p className={styles.subtitle}>
          Your companion for finding the <span className={styles.accentSoft}>right university</span> and building a
          study plan to get in.
        </p>

        <Roadmap />

        <TransitionLink className={styles.cta} href="/choice">
          Let’s go
        </TransitionLink>
        <p className={styles.ctaNote}>Free to start</p>
      </main>
    </div>
  );
}
