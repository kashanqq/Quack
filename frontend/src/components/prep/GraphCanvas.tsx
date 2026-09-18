"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";
import styles from "./prep.module.css";

/** Canvas offset in screen pixels and the zoom the content is drawn at. */
type View = { x: number; y: number; k: number };

const MIN_K = 0.45;
const MAX_K = 1.8;
const PAD = 28;
/** Below this the pointer counts as a click on the node, not a drag of it */
const SLOP = 3;

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

/** Nodes drag in screen pixels; the current zoom turns those into canvas pixels. */
const ScaleContext = createContext<{ current: number }>({ current: 1 });

export function readStore<T>(key: string): T | null {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

export function writeStore(key: string, value: unknown) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Private mode: the layout just is not remembered.
  }
}

type Props = {
  /** Size of the drawing itself; the viewport shows as much of it as fits */
  width: number;
  height: number;
  label: string;
  /** Extra buttons next to the zoom controls, e.g. "разложить заново" */
  tools?: ReactNode;
  hint?: string;
  /** Where to remember the pan and zoom between visits */
  storageKey?: string;
  children: ReactNode;
};

/**
 * A canvas the way Obsidian does it: the drawing sits in an open plane, the background drags to move
 * it, Ctrl + wheel zooms. Every graph on this screen — and the ones still to come — lives in one.
 */
export function GraphCanvas({ width, height, label, tools, hint, storageKey, children }: Props) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const [view, setView] = useState<View>({ x: 0, y: PAD, k: 1 });
  const [grabbing, setGrabbing] = useState(false);
  /** Nothing is remembered until the map has actually been moved — the first visit always gets a fresh view */
  const [touched, setTouched] = useState(false);
  const pan = useRef<{ id: number; x: number; y: number } | null>(null);
  const scaleRef = useRef(1);
  scaleRef.current = view.k;

  /** Zoom keeping the point under the cursor (or the middle of the viewport) still */
  const zoomAt = useCallback((factor: number, px: number, py: number) => {
    setTouched(true);
    setView((v) => {
      const k = clamp(v.k * factor, MIN_K, MAX_K);
      return { k, x: px - ((px - v.x) / v.k) * k, y: py - ((py - v.y) / v.k) * k };
    });
  }, []);

  const zoomBy = (factor: number) => {
    const box = viewportRef.current?.getBoundingClientRect();
    zoomAt(factor, (box?.width ?? 0) / 2, (box?.height ?? 0) / 2);
  };

  /** The whole drawing at once, however small that turns out */
  const fit = () => {
    const box = viewportRef.current?.getBoundingClientRect();
    if (!box) return;
    setTouched(true);
    const k = clamp(Math.min((box.width - PAD * 2) / width, (box.height - PAD * 2) / height), MIN_K, 1);
    setView({ k, x: (box.width - width * k) / 2, y: Math.max(PAD, (box.height - height * k) / 2) });
  };

  /** What the map opens on: full width, labels still readable, the rest a drag away */
  const fitWidth = useCallback(() => {
    const box = viewportRef.current?.getBoundingClientRect();
    if (!box) return;
    const k = clamp((box.width - PAD * 2) / width, MIN_K, 1);
    setView({ k, x: (box.width - width * k) / 2, y: PAD });
  }, [width]);

  useEffect(() => {
    const stored = storageKey ? readStore<View>(storageKey) : null;
    if (stored && Number.isFinite(stored.k)) setView(stored);
    else fitWidth();
  }, [fitWidth, storageKey]);

  useEffect(() => {
    if (storageKey && touched) writeStore(storageKey, view);
  }, [storageKey, touched, view]);

  // The wheel has to be non-passive to zoom; a plain wheel is left alone so the page still scrolls.
  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        const box = el.getBoundingClientRect();
        zoomAt(Math.exp(-e.deltaY / 320), e.clientX - box.left, e.clientY - box.top);
      } else if (e.shiftKey) {
        e.preventDefault();
        setView((v) => ({ ...v, x: v.x - (e.deltaX || e.deltaY) }));
      }
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [zoomAt]);

  const onPointerDown = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (e.button !== 0 && e.button !== 1) return;
    if ((e.target as HTMLElement).closest("[data-canvas-node]")) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    pan.current = { id: e.pointerId, x: e.clientX, y: e.clientY };
    setGrabbing(true);
  };

  const onPointerMove = (e: ReactPointerEvent<HTMLDivElement>) => {
    const p = pan.current;
    if (!p || p.id !== e.pointerId) return;
    setTouched(true);
    const dx = e.clientX - p.x;
    const dy = e.clientY - p.y;
    p.x = e.clientX;
    p.y = e.clientY;
    setView((v) => ({ ...v, x: v.x + dx, y: v.y + dy }));
  };

  const endPan = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (pan.current?.id !== e.pointerId) return;
    pan.current = null;
    setGrabbing(false);
  };

  return (
    <div className={styles.canvasFrame}>
      <div
        ref={viewportRef}
        className={`${styles.canvasViewport} ${grabbing ? styles.canvasGrabbing : ""}`}
        aria-label={label}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endPan}
        onPointerCancel={endPan}
      >
        <div
          className={styles.canvasWorld}
          style={{ width, height, transform: `translate(${view.x}px, ${view.y}px) scale(${view.k})` }}
        >
          <ScaleContext.Provider value={scaleRef}>{children}</ScaleContext.Provider>
        </div>

        {/* The controls sit inside the viewport, so they have to keep their presses out of the pan */}
        <div className={styles.canvasTools} onPointerDown={(e) => e.stopPropagation()}>
          <button type="button" onClick={() => zoomBy(1 / 1.2)} aria-label="Отдалить">
            −
          </button>
          <span className={styles.canvasZoom}>{Math.round(view.k * 100)}%</span>
          <button type="button" onClick={() => zoomBy(1.2)} aria-label="Приблизить">
            +
          </button>
          <button type="button" onClick={fit}>
            по размеру
          </button>
          {tools}
        </div>

        {/* The hint rides in the corner of the canvas instead of taking a line under it */}
        {hint && <p className={styles.canvasHint}>{hint}</p>}
      </div>
    </div>
  );
}

type Drag = { id: string; pointer: number; px: number; py: number; ox: number; oy: number; moved: boolean };

/**
 * Dragging for the nodes inside a GraphCanvas. A press that does not travel still selects the node, so
 * the map keeps working for anyone who never drags anything.
 */
export function useNodeDrag(onMove: (id: string, x: number, y: number) => void) {
  const scale = useContext(ScaleContext);
  const drag = useRef<Drag | null>(null);
  const settled = useRef(false);
  const [dragging, setDragging] = useState<string | null>(null);

  const bind = (id: string, at: { x: number; y: number }) => ({
    "data-canvas-node": true,
    onPointerDown: (e: ReactPointerEvent<HTMLElement>) => {
      if (e.button !== 0) return;
      e.stopPropagation(); // the canvas behind must not start panning as well
      e.currentTarget.setPointerCapture(e.pointerId);
      drag.current = { id, pointer: e.pointerId, px: e.clientX, py: e.clientY, ox: at.x, oy: at.y, moved: false };
    },
    onPointerMove: (e: ReactPointerEvent<HTMLElement>) => {
      const d = drag.current;
      if (!d || d.pointer !== e.pointerId) return;
      const dx = e.clientX - d.px;
      const dy = e.clientY - d.py;
      if (!d.moved) {
        if (Math.hypot(dx, dy) < SLOP) return;
        d.moved = true;
        setDragging(d.id);
      }
      onMove(d.id, d.ox + dx / scale.current, d.oy + dy / scale.current);
    },
    onPointerUp: (e: ReactPointerEvent<HTMLElement>) => {
      const d = drag.current;
      if (!d || d.pointer !== e.pointerId) return;
      drag.current = null;
      settled.current = d.moved;
      setDragging(null);
    },
    onPointerCancel: () => {
      drag.current = null;
      setDragging(null);
    },
  });

  /** True once for the click that ends a drag, so it does not also count as a tap on the node */
  const tookOver = () => {
    const was = settled.current;
    settled.current = false;
    return was;
  };

  return { bind, dragging, tookOver };
}
