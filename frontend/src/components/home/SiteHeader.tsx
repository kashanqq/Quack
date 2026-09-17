import Link from "next/link";
import styles from "./home.module.css";

export function SiteHeader() {
  return (
    <header className={styles.header}>
      <Link className={styles.logo} href="/">
        Quack<span className={styles.accent}>!</span>
      </Link>

      <nav className={styles.nav} aria-label="Main">
        <div className={styles.navItem}>
          <a href="#possibilities">Possibilities</a>
          <div className={`${styles.dropdown} ${styles.dropdownStacked}`}>
            <a href="#preparation">Preparation</a>
            <a href="#choice">Choice</a>
          </div>
        </div>
        <div className={styles.navItem}>
          <a href="#resources">Resources</a>
          <div className={`${styles.dropdown} ${styles.dropdownRow}`}>
            <a href="#how-it-works">How it works</a>
            <a href="#about">About us</a>
          </div>
        </div>
        <div className={styles.navItem}>
          <a href="#pricing">Pricing</a>
        </div>
      </nav>

      <div className={styles.auth}>
        <a className={styles.login} href="#login">
          Log In
        </a>
        <a className={styles.signin} href="#signin">
          <span className={styles.signinBg} aria-hidden="true" />
          <span className={styles.signinText}>Sign In</span>
          <img className={styles.signinArrow} src="/assets/arrow.svg" alt="" />
        </a>
      </div>
    </header>
  );
}
