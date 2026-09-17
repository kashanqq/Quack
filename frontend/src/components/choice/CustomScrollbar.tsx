"use client";

import { useEffect, useRef, type RefObject } from "react";
import styles from "./choice.module.css";

type CustomScrollbarProps = {
  target: RefObject<HTMLElement | null>;
  className: string;
};

/** Scrollbar from the design: arrow buttons plus a draggable thumb, bound to `target`. */
export function CustomScrollbar({ target, className }: CustomScrollbarProps) {
  const barRef = useRef<HTMLDivElement>(null);
  const railRef = useRef<HTMLDivElement>(null);
  const thumbRef = useRef<HTMLDivElement>(null);

  const metrics = () => {
    const scroller = target.current!;
    const { scrollHeight: sh, clientHeight: ch } = scroller;
    const railH = railRef.current!.clientHeight;
    const thumbH = sh <= ch ? railH : Math.max(40, (railH * ch) / sh);
    return { scroller, sh, ch, railH, thumbH };
  };

  useEffect(() => {
    const scroller = target.current;
    if (!scroller) return;

    const update = () => {
      const { sh, ch, railH, thumbH } = metrics();
      const top = sh <= ch ? 0 : (scroller.scrollTop / (sh - ch)) * (railH - thumbH);
      thumbRef.current!.style.height = `${thumbH}px`;
      thumbRef.current!.style.transform = `translateY(${top}px)`;
      barRef.current!.classList.toggle(styles.isIdle, sh <= ch);
    };

    scroller.addEventListener("scroll", update, { passive: true });
    const resize = new ResizeObserver(update);
    resize.observe(scroller);
    const mutations = new MutationObserver(update);
    mutations.observe(scroller, { childList: true, subtree: true, characterData: true });
    update();

    return () => {
      scroller.removeEventListener("scroll", update);
      resize.disconnect();
      mutations.disconnect();
    };
  }, [target]);

  const scrollByStep = (dir: number) => target.current?.scrollBy({ top: dir * 140, behavior: "smooth" });

  const onThumbDown = (e: React.PointerEvent<HTMLDivElement>) => {
    e.preventDefault();
    const thumb = e.currentTarget;
    const { scroller, sh, ch, railH, thumbH } = metrics();
    const startY = e.clientY;
    const startTop = scroller.scrollTop;
    const ratio = (sh - ch) / Math.max(1, railH - thumbH);

    thumb.setPointerCapture(e.pointerId);
    thumb.classList.add(styles.isDragging);
    const move = (ev: PointerEvent) => (scroller.scrollTop = startTop + (ev.clientY - startY) * ratio);
    const up = () => {
      thumb.classList.remove(styles.isDragging);
      thumb.removeEventListener("pointermove", move);
    };
    thumb.addEventListener("pointermove", move);
    thumb.addEventListener("pointerup", up, { once: true });
  };

  const onRailClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === thumbRef.current) return;
    const { scroller, sh, ch, railH } = metrics();
    const y = e.clientY - e.currentTarget.getBoundingClientRect().top;
    scroller.scrollTo({ top: (y / railH) * (sh - ch), behavior: "smooth" });
  };

  return (
    <div ref={barRef} className={`${styles.scrollbar} ${className}`}>
      <button className={styles.scrollbarArrow} type="button" aria-label="Прокрутить вверх" onClick={() => scrollByStep(-1)}>
        <img src="/assets/scroll-up.svg" alt="" />
      </button>
      <div ref={railRef} className={styles.scrollbarRail} onClick={onRailClick}>
        <div ref={thumbRef} className={styles.scrollbarThumb} onPointerDown={onThumbDown} />
      </div>
      <button className={styles.scrollbarArrow} type="button" aria-label="Прокрутить вниз" onClick={() => scrollByStep(1)}>
        <img src="/assets/scroll-down.svg" alt="" />
      </button>
    </div>
  );
}
