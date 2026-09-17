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
          <a href="#possibilities">{t.possibilities}</a>
          <div className={`${styles.dropdown} ${styles.dropdownStacked}`}>
            <a href="#preparation">{t.preparation}</a>
            <a href="#choice">{t.choice}</a>
          </div>
        </div>
        <div className={styles.navItem}>
          <a href="#resources">{t.resources}</a>
          <div className={`${styles.dropdown} ${styles.dropdownRow}`}>
            <a href="#how-it-works">{t.howItWorks}</a>
            <a href="#about">{t.about}</a>
          </div>
        </div>
        <div className={styles.navItem}>
          <a href="#pricing">{t.pricing}</a>
        </div>
      </nav>

      <div className={styles.auth}>
        <a className={styles.login} href="#login">
          {t.login}
        </a>
        <a className={styles.signin} href="#signup" data-aura>
          <span className={styles.signinBg} aria-hidden="true" />
          <span className={styles.signinText}>{t.signup}</span>
          <img className={styles.signinArrow} src="/assets/arrow.svg" alt="" />
        </a>
      </div>
    </header>
  );
}
