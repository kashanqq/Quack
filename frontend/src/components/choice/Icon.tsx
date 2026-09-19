import type { CSSProperties } from "react";
import styles from "./layout.module.css";

export type IconName =
  | "arrow-down"
  | "arrow-left"
  | "arrow-up"
  | "book-open-check"
  | "calendar-days"
  | "calendar-plus"
  | "check"
  | "chevron-right"
  | "external-link"
  | "flag"
  | "gauge"
  | "circle-check"
  | "git-compare"
  | "graduation-cap"
  | "history"
  | "info"
  | "layers"
  | "layout-dashboard"
  | "list-checks"
  | "menu"
  | "message-circle"
  | "message-square"
  | "network"
  | "panel-left-close"
  | "panel-left-open"
  | "panel-right-close"
  | "panel-right-open"
  | "pencil"
  | "play"
  | "plus"
  | "route"
  | "settings"
  | "sparkles"
  | "star"
  | "target"
  | "trash-2"
  | "trending-down"
  | "trending-up"
  | "triangle-alert"
  | "user-round"
  | "x";

/** Lucide icon from /public/assets, painted with the current text colour through a mask. */
export function Icon({ name, size = 20, className }: { name: IconName; size?: number; className?: string }) {
  const style = { "--icon": `url(/assets/icon-${name}.svg)`, width: size, height: size } as CSSProperties;
  return <span className={[styles.icon, className].filter(Boolean).join(" ")} style={style} aria-hidden="true" />;
}
