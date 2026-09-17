"use client";

import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import styles from "./reveal.module.css";

type RevealProps = {
  children: ReactNode;
  /** Seconds to wait after the element enters the viewport, for staggering siblings. */
  delay?: number;
  /** Direction the element travels in from. */
  from?: "up" | "left" | "right";
  className?: string;
};

/**
 * Fades an element in as it scrolls into view. The background grid stays put,
 * so only the content appears to arrive.
 */
export function Reveal({ children, delay = 0, from = "up", className }: RevealProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setShown(true);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          observer.disconnect();
          setShown(true);
        }
      },
      // Fire a little before the element is fully on screen.
      { threshold: 0.15, rootMargin: "0px 0px -8% 0px" }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={[styles.reveal, styles[from], shown && styles.shown, className].filter(Boolean).join(" ")}
      style={{ "--delay": `${delay}s` } as CSSProperties}
    >
      {children}
    </div>
  );
}
