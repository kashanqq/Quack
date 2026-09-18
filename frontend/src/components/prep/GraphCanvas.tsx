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
import { store } from "../account/store";
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
/** A wheel gesture counts as finished after this long without another tick */
const WHEEL_SETTLE_MS = 400;

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

/**
 * A text selection left on the page turns the next press into a native drag of that text, and the
 * canvas stops moving until it is cleared — so every press on the canvas drops it first.
 */
const dropSelection = () => window.getSelection()?.removeAllRanges();

/** Nodes drag in screen pixels; the current zoom turns those into canvas pixels. */
const ScaleContext = createContext<{ current: number }>({ current: 1 });

type Props = {
  /** Size of the drawing itself; the viewport shows as much of it as fits */
  width: number;
  height: number;
  label: string;
  /** Extra buttons next to the zoom controls, e.g. "разложить заново" */
  tools?: ReactNode;
  hint?: string;
  /** Where to remember the pan and zoom between visits; saved when a gesture ends, not while it runs */
  storageKey?: string;
  /** A card pinned beside a point of the drawing; it follows the point but never scales with the zoom */
  popover?: Popover | null;
  /** A press on the empty background that did not turn into a pan */
  onBackgroundTap?: () => void;
  /** Points that must not be missed: while one is off screen, an arrow at the edge points its way */
  beacons?: Beacon[];
  children: ReactNode;
};

export type Beacon = { id: string; at: { x: number; y: number }; label: string; tone: "root" | "trap" };

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
export function GraphCanvas({ width, height, label, tools, hint, storageKey, popover, onBackgroundTap, beacons, children }: Props) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const [view, setView] = useState<View>({ x: 0, y: PAD, k: 1 });
  const [grabbing, setGrabbing] = useState(false);
  /** A short glide when the view jumps to a point, so the student sees where the map went */
  const [gliding, setGliding] = useState(false);
  /**
   * The view is saved once a gesture is over — the pan released, the wheel settled, a button pressed —
   * never on every frame of it. Until the map is moved, nothing is saved and every visit opens fresh.
   */
  const [commits, setCommits] = useState(0);
  const commit = useCallback(() => setCommits((c) => c + 1), []);
  const viewRef = useRef(view);
  viewRef.current = view;
  const pan = useRef<{ id: number; x: number; y: number; sx: number; sy: number; moved: boolean } | null>(null);
  const [box, setBox] = useState({ w: 0, h: 0 });
  const scaleRef = useRef(1);
  scaleRef.current = view.k;

  /** Zoom keeping the point under the cursor (or the middle of the viewport) still */
  const zoomAt = useCallback((factor: number, px: number, py: number) => {
    setView((v) => {
      const k = clamp(v.k * factor, MIN_K, MAX_K);
      return { k, x: px - ((px - v.x) / v.k) * k, y: py - ((py - v.y) / v.k) * k };
    });
  }, []);

  const zoomBy = (factor: number) => {
    const box = viewportRef.current?.getBoundingClientRect();
    zoomAt(factor, (box?.width ?? 0) / 2, (box?.height ?? 0) / 2);
    commit();
  };

  /** The whole drawing at once, however small that turns out */
  const fit = () => {
    const box = viewportRef.current?.getBoundingClientRect();
    if (!box) return;
    commit();
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

  /** Brings a point of the drawing to the middle of the viewport */
  const focusOn = (at: { x: number; y: number }) => {
    setGliding(true);
    setView((v) => ({ ...v, x: box.w / 2 - at.x * v.k, y: box.h / 2 - at.y * v.k }));
    commit();
    window.setTimeout(() => setGliding(false), 480);
  };

  useEffect(() => {
    const stored = storageKey ? store.get<View>(storageKey) : null;
    if (stored && Number.isFinite(stored.k)) setView(stored);
    else fitWidth();
  }, [fitWidth, storageKey]);

  // Runs after the render that applied the gesture's last step, so it saves where the map came to rest
  useEffect(() => {
    if (commits && storageKey) store.set(storageKey, viewRef.current);
  }, [commits, storageKey]);

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
    let settle: ReturnType<typeof setTimeout> | undefined;
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
      } else {
        return;
      }
      // A wheel has no "release": the gesture is over once the ticks stop
      clearTimeout(settle);
      settle = setTimeout(commit, WHEEL_SETTLE_MS);
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => {
      clearTimeout(settle);
      el.removeEventListener("wheel", onWheel);
    };
  }, [commit, zoomAt]);

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
    if (p.moved) commit();
    else if (e.type === "pointerup") onBackgroundTap?.();
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
          className={`${styles.canvasWorld} ${gliding ? styles.canvasGliding : ""}`}
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

        {beacons && box.w > 0 && <Beacons beacons={beacons} view={view} box={box} onGo={focusOn} />}

        {popover && box.w > 0 && <PopoverCard popover={popover} view={view} box={box} />}
      </div>
    </div>
  );
}

/** How far inside the viewport edge the arrows ride, and how close to each other they may sit */
const BEACON_INSET = 40;
const BEACON_APART = 44;

/**
 * Arrows for the points that are off screen. Each sits where the line from the middle of the viewport
 * to its point leaves an inner ellipse — a root below the view gets an arrow at the bottom, pointing
 * down — and a press glides the map to it.
 */
function Beacons({
  beacons,
  view,
  box,
  onGo,
}: {
  beacons: Beacon[];
  view: View;
  box: { w: number; h: number };
  onGo: (at: { x: number; y: number }) => void;
}) {
  const cx = box.w / 2;
  const cy = box.h / 2;
  const rx = Math.max(cx - BEACON_INSET, 1);
  const ry = Math.max(cy - BEACON_INSET, 1);
  const placed: { x: number; y: number }[] = [];

  return (
    <>
      {beacons.map((b) => {
        const sx = b.at.x * view.k + view.x;
        const sy = b.at.y * view.k + view.y;
        if (sx > 16 && sx < box.w - 16 && sy > 16 && sy < box.h - 16) return null; // on screen: the node shows itself

        const dx = sx - cx;
        const dy = sy - cy;
        const t = 1 / Math.sqrt((dx * dx) / (rx * rx) + (dy * dy) / (ry * ry));
        // The label is wider than the arrow: keep the whole chip inside the viewport
        const half = (40 + b.label.length * 6.6) / 2;
        const x = clamp(cx + dx * t, half + 8, box.w - half - 8);
        const y = clamp(cy + dy * t, 22, box.h - 22);
        if (placed.some((p) => Math.hypot(p.x - x, p.y - y) < BEACON_APART)) return null;
        placed.push({ x, y });

        return (
          <button
            key={b.id}
            type="button"
            className={styles.beacon}
            data-tone={b.tone}
            style={{ left: x, top: y }}
            aria-label={`Показать на карте — ${b.label}`}
            title="Показать на карте"
            data-canvas-chrome
            onPointerDown={(e) => e.stopPropagation()}
            onClick={() => onGo(b.at)}
          >
            <svg className={styles.beaconArrow} style={{ rotate: `${Math.atan2(dy, dx)}rad` }} viewBox="0 0 16 16" aria-hidden="true">
              <path d="M2 8h11M9 3.5 13.5 8 9 12.5" />
            </svg>
            {b.label}
          </button>
        );
      })}
    </>
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
export function useNodeDrag(onMove: (id: string, x: number, y: number) => void, onDrop?: (id: string) => void) {
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
      if (d.moved) onDrop?.(d.id);
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
