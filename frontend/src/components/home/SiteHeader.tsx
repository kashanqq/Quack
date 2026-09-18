import Link from "next/link";
import { copy } from "./copy";
import styles from "./home.module.css";

export function SiteHeader() {
  const t = copy.nav;

  return (
    <header className={styles.header}>
      <Link className={styles.logo} href="/">
        Quack<span className={styles.accent}>!</span>
      </Link>

      <nav className={styles.nav} aria-label="Основная навигация">
        <div className={styles.navItem}>
          <a href="/#possibilities">
            {t.possibilities}
            <Chevron />
          </a>
          <div className={`${styles.dropdown} ${styles.dropdownStacked}`}>
            <a href="/#preparation">{t.preparation}</a>
            <a href="/#choice">{t.choice}</a>
          </div>
        </div>
        <div className={styles.navItem}>
          <a href="/#resources">
            {t.resources}
            <Chevron />
          </a>
          <div className={`${styles.dropdown} ${styles.dropdownStacked}`}>
            <a href="/#how-it-works">{t.howItWorks}</a>
            <a href="/#about">{t.about}</a>
          </div>
        </div>
        <div className={styles.navItem}>
          <Link href="/pricing">{t.pricing}</Link>
        </div>
      </nav>

      <div className={styles.auth}>
        <a className={styles.login} href="/login">
          {t.login}
        </a>
        <a className={styles.signin} href="/login?mode=signup" data-aura>
          <span className={styles.signinBg} aria-hidden="true" />
          <span className={styles.signinText}>{t.signup}</span>
          <img className={styles.signinArrow} src="/assets/arrow.svg" alt="" />
        </a>
      </div>
    </header>
  );
}

/** Marks the items that open a menu; it turns over while the menu is open. */
function Chevron() {
  return (
    <svg className={styles.chevron} viewBox="0 0 10 6" aria-hidden="true">
      <path d="M1 1l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
