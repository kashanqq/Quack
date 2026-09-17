"use client";

import styles from "./layout.module.css";

type ResizeHandleProps = {
  side: "left" | "right";
  label: string;
  value: number;
  min: number;
  max: number;
  onDragStart: () => void;
  /** Horizontal distance from the drag start, in px */
  onDrag: (dx: number) => void;
  onDragEnd: () => void;
  /** Keyboard nudge in px (arrow keys) */
  onNudge: (dx: number) => void;
};

/** Thin draggable edge between a side panel and the chat. */
export function ResizeHandle({ side, label, value, min, max, onDragStart, onDrag, onDragEnd, onNudge }: ResizeHandleProps) {
  return (
    <div
      className={`${styles.handle} ${side === "left" ? styles.handleLeft : styles.handleRight}`}
      role="separator"
      aria-orientation="vertical"
      aria-label={label}
      aria-valuenow={Math.round(value)}
      aria-valuemin={min}
      aria-valuemax={max}
      tabIndex={0}
      onPointerDown={(e) => {
        e.preventDefault();
        const el = e.currentTarget;
        const startX = e.clientX;
        try {
          el.setPointerCapture(e.pointerId);
        } catch {}
        onDragStart();
        const move = (ev: PointerEvent) => onDrag(ev.clientX - startX);
        let done = false;
        const up = () => {
          if (done) return;
          done = true;
          el.removeEventListener("pointermove", move);
          onDragEnd();
        };
        el.addEventListener("pointermove", move);
        el.addEventListener("pointerup", up, { once: true });
        el.addEventListener("pointercancel", up, { once: true });
      }}
      onKeyDown={(e) => {
        if (e.key === "ArrowLeft") onNudge(-24);
        if (e.key === "ArrowRight") onNudge(24);
      }}
    />
  );
}
