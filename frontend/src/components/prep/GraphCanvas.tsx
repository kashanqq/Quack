"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";
import styles from "./prep.module.css";

/** Canvas offset in screen pixels and the zoom the content is drawn at. */
type View = { x: number; y: number; k: number };

const MIN_K = 0.45;
const MAX_K = 1.8;
const PAD = 28;
/** On a narrow canvas the margins around a fitted drawing shrink, every pixel goes to the graph */
const PAD_NARROW = 8;
/** Below this the pointer counts as a click on the node, not a drag of it */
const SLOP = 3;
/** The popover card: its width, and how close it may come to the canvas edge */
const POP_W = 320;
const EDGE = 12;
/** The card starts below the zoom controls, so it never covers them */
const TOP_EDGE = 54;
/** Narrower than this, the card turns into a sheet along the bottom of the canvas */
const SHEET_BELOW = 560;

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

/**
 * A text selection left on the page turns the next press into a native drag of that text, and the
 * canvas stops moving until it is cleared — so every press on the canvas drops it first.
 */
const dropSelection = () => window.getSelection()?.removeAllRanges();

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
  /** A card pinned beside a point of the drawing; it follows the point but never scales with the zoom */
  popover?: Popover | null;
  /** A press on the empty background that did not turn into a pan */
  onBackgroundTap?: () => void;
  children: ReactNode;
};

type Popover = {
  /** The point in drawing coordinates, and how far to the side of it the card starts */
  at: { x: number; y: number };
  gap: number;
  label: string;
  content: ReactNode;
  onClose: () => void;
};

/**
 * A canvas the way Obsidian does it: the drawing sits in an open plane, the background drags to move
 * it, Ctrl + wheel zooms. Every graph on this screen — and the ones still to come — lives in one.
 */
export function GraphCanvas({ width, height, label, tools, hint, storageKey, popover, onBackgroundTap, children }: Props) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const [view, setView] = useState<View>({ x: 0, y: PAD, k: 1 });
  const [grabbing, setGrabbing] = useState(false);
  /** Nothing is remembered until the map has actually been moved — the first visit always gets a fresh view */
  const [touched, setTouched] = useState(false);
  const pan = useRef<{ id: number; x: number; y: number; sx: number; sy: number; moved: boolean } | null>(null);
  const [box, setBox] = useState({ w: 0, h: 0 });
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
    const pad = box.width < SHEET_BELOW ? PAD_NARROW : PAD;
    const k = clamp((box.width - pad * 2) / width, MIN_K, 1);
    setView({ k, x: (box.width - width * k) / 2, y: pad });
  }, [width]);

  useEffect(() => {
    const stored = storageKey ? readStore<View>(storageKey) : null;
    if (stored && Number.isFinite(stored.k)) setView(stored);
    else fitWidth();
  }, [fitWidth, storageKey]);

  useEffect(() => {
    if (storageKey && touched) writeStore(storageKey, view);
  }, [storageKey, touched, view]);

  // Measured before the first paint as well, not only when the observer gets round to it
  useLayoutEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    const measure = () => setBox({ w: el.clientWidth, h: el.clientHeight });
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const closePopover = popover?.onClose;
  useEffect(() => {
    if (!closePopover) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && closePopover();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [closePopover]);

  // The wheel has to be non-passive to zoom; a plain wheel is left alone so the page still scrolls.
  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      // Over the popover or the controls the wheel belongs to them, e.g. to scroll a long card
      if ((e.target as HTMLElement).closest?.("[data-canvas-chrome]")) return;
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
    e.preventDefault(); // no text selection starting from the background
    dropSelection();
    e.currentTarget.setPointerCapture(e.pointerId);
    pan.current = { id: e.pointerId, x: e.clientX, y: e.clientY, sx: e.clientX, sy: e.clientY, moved: false };
    setGrabbing(true);
  };

  const onPointerMove = (e: ReactPointerEvent<HTMLDivElement>) => {
    const p = pan.current;
    if (!p || p.id !== e.pointerId) return;
    if (!p.moved && Math.hypot(e.clientX - p.sx, e.clientY - p.sy) < SLOP) return;
    p.moved = true;
    setTouched(true);
    const dx = e.clientX - p.x;
    const dy = e.clientY - p.y;
    p.x = e.clientX;
    p.y = e.clientY;
    setView((v) => ({ ...v, x: v.x + dx, y: v.y + dy }));
  };

  const endPan = (e: ReactPointerEvent<HTMLDivElement>) => {
    const p = pan.current;
    if (p?.id !== e.pointerId) return;
    pan.current = null;
    setGrabbing(false);
    if (!p.moved && e.type === "pointerup") onBackgroundTap?.();
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
        onDragStart={(e) => e.preventDefault()}
      >
        <div
          className={styles.canvasWorld}
          style={{ width, height, transform: `translate(${view.x}px, ${view.y}px) scale(${view.k})` }}
        >
          <ScaleContext.Provider value={scaleRef}>{children}</ScaleContext.Provider>
        </div>

        {/* The controls sit inside the viewport, so they have to keep their presses out of the pan */}
        <div className={styles.canvasTools} data-canvas-chrome onPointerDown={(e) => e.stopPropagation()}>
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

        {popover && box.w > 0 && <PopoverCard popover={popover} view={view} box={box} />}
      </div>
    </div>
  );
}

/**
 * The card beside the selected point. It lives in screen space, so the text stays the same size at any
 * zoom; it takes whichever side of the point has room and slides to stay inside the canvas.
 */
function PopoverCard({ popover, view, box }: { popover: Popover; view: View; box: { w: number; h: number } }) {
  const ref = useRef<HTMLDivElement>(null);
  const [cardH, setCardH] = useState(0);

  // The card's height depends on its content, and the vertical clamp needs it
  useLayoutEffect(() => {
    const h = ref.current?.offsetHeight ?? 0;
    if (h !== cardH) setCardH(h);
  });

  let style: CSSProperties;
  if (box.w < SHEET_BELOW) {
    style = { left: EDGE, right: EDGE, bottom: EDGE, maxHeight: box.h * 0.62 };
  } else {
    const px = popover.at.x * view.k + view.x;
    const py = popover.at.y * view.k + view.y;
    const reach = popover.gap * view.k + 14;
    const right = px + reach;
    const left = px - reach - POP_W;
    let x: number;
    if (right + POP_W <= box.w - EDGE) x = right;
    else if (left >= EDGE) x = left;
    else x = box.w - right >= px - reach ? box.w - POP_W - EDGE : EDGE;
    const y = clamp(py - 44, TOP_EDGE, Math.max(TOP_EDGE, box.h - cardH - EDGE));
    style = { left: x, top: y, width: POP_W, maxHeight: box.h - TOP_EDGE - EDGE };
  }

  return (
    <div
      ref={ref}
      className={styles.canvasPopover}
      style={style}
      role="dialog"
      aria-label={popover.label}
      data-canvas-chrome
      onPointerDown={(e) => e.stopPropagation()}
    >
      <button type="button" className={styles.canvasPopoverClose} onClick={popover.onClose} aria-label="Закрыть">
        ×
      </button>
      {popover.content}
    </div>
  );
}

/** The app's phone width (PHONE_MAX in ChoiceApp) */
const PHONE_QUERY = "(max-width: 760px)";

/**
 * On phones every graph runs top to bottom instead of left to right: a phone is tall and narrow, so a
 * graph laid along its length stays readable at full size and only needs scrolling one way.
 */
export function useVertical() {
  const [vertical, setVertical] = useState(false);
  useEffect(() => {
    const query = window.matchMedia(PHONE_QUERY);
    const update = () => setVertical(query.matches);
    update();
    // Some browsers (and device emulation) skip the query's change event, a resize always arrives
    query.addEventListener("change", update);
    window.addEventListener("resize", update);
    return () => {
      query.removeEventListener("change", update);
      window.removeEventListener("resize", update);
    };
  }, []);
  return vertical;
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
      dropSelection();
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
