import { copy } from "./copy";
import { PixelDuck } from "@/components/duck/PixelDuck";
import styles from "./quack.module.css";

/**
 * Three ducks moving at three speeds. Same duck, same size, same billing —
 * the only difference is the beat, so no tempo reads as the "right" one.
 */
export function TempoDucks() {
  const t = copy.quack.tempo;

  return (
    <div className={styles.tempo}>
      <h3 className={styles.tempoHeading}>{t.heading}</h3>

      <ul className={styles.tempoList}>
        {t.ducks.map((duck) => (
          <li key={duck.tempo} className={styles.tempoItem}>
            <span className={styles.tempoDuck}>
              <PixelDuck tempo={duck.tempo} />
            </span>
            <span className={styles.tempoName}>{duck.name}</span>
            <span className={styles.tempoNote}>{duck.note}</span>
          </li>
        ))}
      </ul>

      <p className={styles.tempoFooter}>{t.footer}</p>
      <p className={styles.tempoCaption}>{t.caption}</p>
    </div>
  );
}
