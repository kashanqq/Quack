import Link from "next/link";
import { copy } from "./copy";
import styles from "./footer.module.css";

/** The page footer: the logo, the same links as the header, and the small print. */
export function SiteFooter() {
  const t = copy.footer;
  const nav = copy.nav;

  const columns = [
    {
      title: t.product,
      links: [
        { href: "#preparation", label: nav.preparation },
        { href: "#choice", label: nav.choice },
        { href: "#pricing", label: nav.pricing },
      ],
    },
    {
      title: t.company,
      links: [
        { href: "#how-it-works", label: nav.howItWorks },
        { href: "#about", label: nav.about },
      ],
    },
    {
      title: t.account,
      links: [
        { href: "#login", label: nav.login },
        { href: "#signup", label: nav.signup },
      ],
    },
  ];

  return (
    <footer className={styles.footer}>
      <div className={styles.top}>
        <div className={styles.brand}>
          <Link className={styles.logo} href="/">
            Quack<span className={styles.accent}>!</span>
          </Link>
          <p className={styles.tagline}>{t.tagline}</p>
        </div>

        <nav className={styles.columns} aria-label={t.product}>
          {columns.map((col) => (
            <div key={col.title} className={styles.column}>
              <p className={styles.columnTitle}>{col.title}</p>
              <ul>
                {col.links.map((link) => (
                  <li key={link.href}>
                    <a href={link.href}>{link.label}</a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>
      </div>

      <div className={styles.bottom}>
        <span>{t.rights}</span>
        <a className={styles.toTop} href="#top">
          {t.toTop} ↑
        </a>
      </div>
    </footer>
  );
}
