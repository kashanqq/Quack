import styles from "./duck.module.css";

type DuckProps = {
  className?: string;
  /** Extra class for the wing, used to attach a flapping animation */
  wingClassName?: string;
};

/** Flat three-colour duck used by the page loader and the flying duck. */
export function Duck({ className, wingClassName }: DuckProps) {
  return (
    <svg className={[styles.duck, className].filter(Boolean).join(" ")} viewBox="0 0 64 48" aria-hidden="true">
      <path fill="var(--duck-body)" d="M3 21 L14 26 L10 32 Z" />
      <ellipse fill="var(--duck-body)" cx="29" cy="31" rx="20" ry="12" />
      <circle fill="var(--duck-body)" cx="46" cy="17" r="9.5" />
      <path fill="var(--duck-beak)" d="M54 15.5 Q63 16.5 62.5 19.5 Q58.5 22.5 53.5 21 Z" />
      <circle fill="#2b2826" cx="48.5" cy="14.5" r="1.7" />
      <path
        className={[styles.wing, wingClassName].filter(Boolean).join(" ")}
        fill="var(--duck-wing)"
        d="M15 28 Q25 16 39 27 Q28 36 15 28 Z"
      />
    </svg>
  );
}
