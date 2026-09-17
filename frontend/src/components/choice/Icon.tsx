import type { CSSProperties } from "react";
import styles from "./layout.module.css";

export type IconName =
  | "arrow-left"
  | "book-open-check"
  | "check"
  | "git-compare"
  | "graduation-cap"
  | "history"
  | "menu"
  | "message-square"
  | "panel-left-close"
  | "panel-left-open"
  | "panel-right-close"
  | "panel-right-open"
  | "pencil"
  | "plus"
  | "sparkles"
  | "star"
  | "trash-2"
  | "user-round"
  | "x";

/** Lucide icon from /public/assets, painted with the current text colour through a mask. */
export function Icon({ name, size = 20, className }: { name: IconName; size?: number; className?: string }) {
  const style = { "--icon": `url(/assets/icon-${name}.svg)`, width: size, height: size } as CSSProperties;
  return <span className={[styles.icon, className].filter(Boolean).join(" ")} style={style} aria-hidden="true" />;
}
