"use client";

import { useEffect, useRef, useState } from "react";
import { PROGRAMS, type Program } from "@/components/choice/programs";
import { copy } from "./copy";
import { countryRu, PROGRAM_COORDS, whereIs } from "./globeData";
import styles from "./globe.module.css";

const RAD = Math.PI / 180;
/** Idle spin, degrees per second. One turn takes about a minute. */
const AUTO_SPIN = 6;
/** Share of the disc a picked country should span; below 1 leaves a margin round it. */
const FILL = 0.72;
/** Zoom limits for a picked country: huge ones still lean in, tiny ones stop before the outline gets coarse. */
const ZOOM_MIN = 1.4;
const ZOOM_MAX = 6;
/** Used when the point is on no country in the outline file. */
const ZOOM_FALLBACK = 3;
/** City labels fade in between these zoom levels. */
const LABEL_FROM = 2.6;
const LABEL_FULL = 4;
/** Inertia left after each frame of coasting. */
const FRICTION = 0.93;
/** A press that moves less than this counts as a click, not a drag. */
const CLICK_SLOP = 5;

type RawWorld = { scale: number; countries: { n: string; r: number[][] }[] };
/** Flat [lon, lat, lon, lat, …] in degrees. */
type Ring = Float64Array;
type Land = { name: string; rings: Ring[] };

/** The file stores delta-encoded integers; undo both to get degrees. */
function decodeWorld(raw: RawWorld): Land[] {
  const s = raw.scale;
  return raw.countries.map((c) => ({
    name: c.n,
    rings: c.r.map((flat) => {
      const out = new Float64Array(flat.length);
      let x = flat[0];
      let y = flat[1];
      out[0] = x / s;
      out[1] = y / s;
      for (let i = 2; i < flat.length; i += 2) {
        x += flat[i];
        y += flat[i + 1];
        out[i] = x / s;
        out[i + 1] = y / s;
      }
      return out;
    }),
  }));
}

/** Shortest way round the circle, so easing never takes the long way. */
function wrapDeg(d: number) {
  return ((((d + 180) % 360) + 360) % 360) - 180;
}

function pointInRing(ring: Ring, lon: number, lat: number) {
  let inside = false;
  const n = ring.length / 2;
  for (let i = 0, j = n - 1; i < n; j = i++) {
    const xi = ring[i * 2];
    const yi = ring[i * 2 + 1];
    const xj = ring[j * 2];
    const yj = ring[j * 2 + 1];
    if (yi > lat !== yj > lat && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

/** Great-circle distance between two lon/lat points, in degrees. */
function arcDeg(lon1: number, lat1: number, lon2: number, lat2: number) {
  const c =
    Math.sin(lat1 * RAD) * Math.sin(lat2 * RAD) +
    Math.cos(lat1 * RAD) * Math.cos(lat2 * RAD) * Math.cos((lon2 - lon1) * RAD);
  return Math.acos(Math.max(-1, Math.min(1, c))) / RAD;
}

/**
 * The country under a point, where to aim so the whole of it is in view, and
 * how far to zoom so it fills the disc. The view is aimed at the middle of the
 * country's outline rather than at the point, so no border ends up cut off at
 * the rim. The orthographic view at zoom z shows everything within asin(1/z)
 * of the centre, so the zoom is picked from the farthest border point.
 */
function frameCountry(world: Land[] | null, lon: number, lat: number) {
  if (world) {
    for (const land of world) {
      const ring = land.rings.find((r) => pointInRing(r, lon, lat));
      if (!ring) continue;
      let minLon = 180, maxLon = -180, minLat = 90, maxLat = -90;
      for (let i = 0; i < ring.length; i += 2) {
        minLon = Math.min(minLon, ring[i]);
        maxLon = Math.max(maxLon, ring[i]);
        minLat = Math.min(minLat, ring[i + 1]);
        maxLat = Math.max(maxLat, ring[i + 1]);
      }
      // An outline across the date line has a meaningless box; aim at the point instead.
      const center: [number, number] =
        maxLon - minLon < 180 ? [(minLon + maxLon) / 2, (minLat + maxLat) / 2] : [lon, lat];
      let reach = 0;
      for (let i = 0; i < ring.length; i += 2) reach = Math.max(reach, arcDeg(center[0], center[1], ring[i], ring[i + 1]));
      const zoom = FILL / Math.sin(Math.min(reach, 80) * RAD);
      return { country: land.name, center, zoom: Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, zoom)) };
    }
  }
  return { country: "", center: [lon, lat] as [number, number], zoom: ZOOM_FALLBACK };
}

type Selection = {
  country: string;
  /** Where the view turns to: the middle of the country. */
  center: [number, number];
  zoom: number;
  program?: Program;
  at?: { lon: number; lat: number };
};

type GlobeProps = {
  /** Called with the picked university, or null once it is let go, so the panel can follow. */
  onPickProgram?: (id: string | null) => void;
};

/**
 * A real globe: orthographic projection on a 2D canvas, drag to spin, our demo
 * universities pinned where they actually are.
 *
 * Clicking a marker or a country stops the spin, turns that spot to face the
 * viewer and zooms in until the country fills the disc, with the cities
 * labelled; a card underneath says what was picked.
 */
export function Globe({ onPickProgram }: GlobeProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [world, setWorld] = useState<Land[] | null>(null);
  const [selected, setSelected] = useState<Selection | null>(null);

  // Live animation state, kept out of React so a spinning globe never re-renders.
  const view = useRef({ lambda: -10, phi: 25, zoom: 1 });
  const target = useRef({ lambda: -10, phi: 25, zoom: 1 });
  const spin = useRef({ auto: true, vx: 0, vy: 0 });
  const selectedRef = useRef<Selection | null>(null);

  useEffect(() => {
    let alive = true;
    fetch("/assets/world-110m.json")
      .then((r) => r.json())
      .then((raw: RawWorld) => {
        if (alive) setWorld(decodeWorld(raw));
      })
      .catch(() => {
        /* The globe simply stays empty if the outline file cannot be loaded. */
      });
    return () => {
      alive = false;
    };
  }, []);

  // The panel follows the pick and lets go with it.
  // A country pick counts too when we have a university there: the panel shows the first one.
  const pickedId =
    selected?.program?.id ??
    (selected ? (PROGRAMS.find((p) => p.country === countryRu(selected.country))?.id ?? null) : null);
  useEffect(() => {
    onPickProgram?.(pickedId);
  }, [pickedId, onPickProgram]);

  useEffect(() => {
    selectedRef.current = selected;
    if (!selected) {
      target.current.zoom = 1;
      spin.current.auto = true;
      return;
    }
    // Turn the picked country to face the viewer.
    target.current.lambda = -selected.center[0];
    target.current.phi = selected.center[1];
    target.current.zoom = selected.zoom;
    spin.current.auto = false;
  }, [selected]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let size = 0;
    let frame = 0;
    let last = performance.now();
    // Labels use the page's text face; the canvas cannot read CSS variables itself.
    const font = getComputedStyle(canvas).fontFamily || "sans-serif";

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      size = canvas.clientWidth;
      canvas.width = Math.round(size * dpr);
      canvas.height = Math.round(size * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    /** Screen position of a lon/lat, plus whether it faces the viewer. */
    const project = (lon: number, lat: number) => {
      const { lambda, phi, zoom } = view.current;
      const l = (lon + lambda) * RAD;
      const p = lat * RAD;
      const cosP = Math.cos(p);
      const x = cosP * Math.sin(l);
      const y = Math.sin(p);
      const z = cosP * Math.cos(l);
      const cp = Math.cos(phi * RAD);
      const sp = Math.sin(phi * RAD);
      const y2 = y * cp - z * sp;
      const z2 = y * sp + z * cp;
      const r = radius() * zoom;
      return { x: size / 2 + x * r, y: size / 2 - y2 * r, front: z2 > 0 };
    };

    const radius = () => size / 2 - 12;

    /** Screen position back to lon/lat, or null when the click missed the globe. */
    const unproject = (px: number, py: number) => {
      const { lambda, phi, zoom } = view.current;
      // Zoomed in, the sphere overflows the disc; only what shows inside it counts.
      if (Math.hypot(px - size / 2, py - size / 2) > radius()) return null;
      const r = radius() * zoom;
      const nx = (px - size / 2) / r;
      const ny = -(py - size / 2) / r;
      const d2 = nx * nx + ny * ny;
      if (d2 > 1) return null;
      const nz = Math.sqrt(1 - d2);
      const cp = Math.cos(phi * RAD);
      const sp = Math.sin(phi * RAD);
      const y = ny * cp + nz * sp;
      const z = -ny * sp + nz * cp;
      return { lon: wrapDeg((Math.atan2(nx, z) / RAD) - lambda), lat: Math.asin(Math.max(-1, Math.min(1, y))) / RAD };
    };

    const drawRings = (land: Land, fill: string, stroke: string) => {
      for (const ring of land.rings) {
        // A ring that crosses the horizon is drawn as the pieces that face us.
        let run: { x: number; y: number }[] = [];
        const flush = () => {
          if (run.length > 2) {
            ctx.beginPath();
            ctx.moveTo(run[0].x, run[0].y);
            for (let i = 1; i < run.length; i++) ctx.lineTo(run[i].x, run[i].y);
            ctx.closePath();
            ctx.fillStyle = fill;
            ctx.fill();
            ctx.strokeStyle = stroke;
            ctx.lineWidth = 0.7;
            ctx.stroke();
          }
          run = [];
        };
        for (let i = 0; i < ring.length; i += 2) {
          const p = project(ring[i], ring[i + 1]);
          if (p.front) run.push(p);
          else flush();
        }
        flush();
      }
    };

    /** A small rounded tag to the right of a pin; the picked one gets a second line. */
    const drawLabel = (x: number, y: number, title: string, sub: string | null, strong: boolean) => {
      const padX = 8;
      const lineH = 15;
      ctx.font = `${strong ? 600 : 400} 12px ${font}`;
      const titleW = ctx.measureText(title).width;
      ctx.font = `400 11px ${font}`;
      const subW = sub ? ctx.measureText(sub).width : 0;
      const w = Math.max(titleW, subW) + padX * 2;
      const h = sub ? lineH * 2 + 8 : lineH + 8;
      // Flip to the left of the pin when there is no room on the right, and never past either edge.
      const left = Math.max(4, Math.min(size - 4 - w, x + 12 + w > size - 4 ? x - 12 - w : x + 12));
      const top = y - h / 2;

      ctx.beginPath();
      ctx.roundRect(left, top, w, h, 8);
      ctx.fillStyle = strong ? "rgba(36,33,32,0.94)" : "rgba(36,33,32,0.78)";
      ctx.fill();
      ctx.strokeStyle = strong ? "rgba(255,122,0,0.55)" : "rgba(255,255,255,0.1)";
      ctx.lineWidth = 1;
      ctx.stroke();

      ctx.font = `${strong ? 600 : 400} 12px ${font}`;
      ctx.fillStyle = strong ? "#fff" : "rgba(255,255,255,0.8)";
      ctx.fillText(title, left + padX, top + 4 + lineH / 2);
      if (sub) {
        ctx.font = `400 11px ${font}`;
        ctx.fillStyle = "rgba(255,255,255,0.55)";
        ctx.fillText(sub, left + padX, top + 4 + lineH * 1.5);
      }
    };

    const draw = () => {
      ctx.clearRect(0, 0, size, size);
      // The disc stays the same size; zooming in scales the sphere behind it, like a lens.
      const r = radius();
      // Not laid out yet: a negative radius would throw and stop the loop.
      if (r <= 0) return;
      const cx = size / 2;
      const cy = size / 2;

      // Ocean, lit from the upper left so the disc reads as a sphere.
      const sea = ctx.createRadialGradient(cx - r * 0.35, cy - r * 0.35, r * 0.1, cx, cy, r);
      sea.addColorStop(0, "#3a3532");
      sea.addColorStop(1, "#1b1917");
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.fillStyle = sea;
      ctx.fill();

      ctx.save();
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.clip();

      // Graticule every 30°, faint enough to read as a globe rather than a grid.
      ctx.strokeStyle = "rgba(255,255,255,0.05)";
      ctx.lineWidth = 0.6;
      for (let lon = -180; lon < 180; lon += 30) {
        ctx.beginPath();
        let started = false;
        for (let lat = -90; lat <= 90; lat += 4) {
          const p = project(lon, lat);
          if (!p.front) {
            started = false;
            continue;
          }
          if (started) ctx.lineTo(p.x, p.y);
          else ctx.moveTo(p.x, p.y);
          started = true;
        }
        ctx.stroke();
      }
      for (let lat = -60; lat <= 60; lat += 30) {
        ctx.beginPath();
        let started = false;
        for (let lon = -180; lon <= 180; lon += 4) {
          const p = project(lon, lat);
          if (!p.front) {
            started = false;
            continue;
          }
          if (started) ctx.lineTo(p.x, p.y);
          else ctx.moveTo(p.x, p.y);
          started = true;
        }
        ctx.stroke();
      }

      const sel = selectedRef.current;
      if (world) {
        for (const land of world) {
          const isSel = sel?.country === land.name;
          drawRings(land, isSel ? "rgba(255,122,0,0.5)" : "#57514c", isSel ? "#ff9a3c" : "rgba(255,255,255,0.14)");
        }
      }

      // University markers, drawn last so they sit on top of the land.
      for (const program of PROGRAMS) {
        const coords = PROGRAM_COORDS[program.id];
        if (!coords) continue;
        const p = project(coords[0], coords[1]);
        if (!p.front) continue;
        const isSel = sel?.program?.id === program.id;
        ctx.beginPath();
        ctx.arc(p.x, p.y, isSel ? 11 : 8, 0, Math.PI * 2);
        ctx.fillStyle = isSel ? "rgba(255,122,0,0.35)" : "rgba(255,122,0,0.18)";
        ctx.fill();
        ctx.beginPath();
        ctx.arc(p.x, p.y, isSel ? 4.5 : 3.2, 0, Math.PI * 2);
        ctx.fillStyle = "#ff7a00";
        ctx.fill();
      }

      // Zoomed in, the pins get names: the city for each, the university for the picked one.
      const labels = Math.max(0, Math.min(1, (view.current.zoom - LABEL_FROM) / (LABEL_FULL - LABEL_FROM)));
      if (labels > 0) {
        ctx.globalAlpha = labels;
        ctx.textBaseline = "middle";
        for (const program of PROGRAMS) {
          const coords = PROGRAM_COORDS[program.id];
          if (!coords) continue;
          const p = project(coords[0], coords[1]);
          if (!p.front) continue;
          const isSel = sel?.program?.id === program.id;
          drawLabel(p.x, p.y, isSel ? program.university : program.city, isSel ? program.city : null, isSel);
        }
        ctx.globalAlpha = 1;
      }
      ctx.restore();

      // Rim light along the limb.
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(255,255,255,0.14)";
      ctx.lineWidth = 1;
      ctx.stroke();
    };

    const tick = (now: number) => {
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;
      const v = view.current;
      const t = target.current;

      if (spin.current.auto && !reduced) {
        v.lambda += AUTO_SPIN * dt;
        t.lambda = v.lambda;
        t.phi = v.phi;
      } else {
        // Coast after a drag, then settle onto the selected target.
        if (Math.abs(spin.current.vx) > 0.01 || Math.abs(spin.current.vy) > 0.01) {
          v.lambda += spin.current.vx;
          v.phi = Math.max(-80, Math.min(80, v.phi + spin.current.vy));
          spin.current.vx *= FRICTION;
          spin.current.vy *= FRICTION;
          t.lambda = v.lambda;
          t.phi = v.phi;
        } else {
          v.lambda += wrapDeg(t.lambda - v.lambda) * 0.08;
          v.phi += (t.phi - v.phi) * 0.08;
        }
      }
      v.zoom += (t.zoom - v.zoom) * 0.08;

      draw();
      frame = requestAnimationFrame(tick);
    };

    resize();
    frame = requestAnimationFrame(tick);
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);

    // --- dragging -------------------------------------------------------

    let dragging = false;
    let moved = 0;
    let lastX = 0;
    let lastY = 0;

    const onDown = (e: PointerEvent) => {
      dragging = true;
      moved = 0;
      lastX = e.clientX;
      lastY = e.clientY;
      spin.current.auto = false;
      spin.current.vx = 0;
      spin.current.vy = 0;
      canvas.setPointerCapture(e.pointerId);
    };

    const onMove = (e: PointerEvent) => {
      if (!dragging) return;
      const dx = e.clientX - lastX;
      const dy = e.clientY - lastY;
      lastX = e.clientX;
      lastY = e.clientY;
      moved += Math.abs(dx) + Math.abs(dy);
      // Slower when zoomed in, so the country under the finger moves with it.
      const k = 0.25 / view.current.zoom;
      view.current.lambda += dx * k;
      view.current.phi = Math.max(-80, Math.min(80, view.current.phi + dy * k));
      target.current.lambda = view.current.lambda;
      target.current.phi = view.current.phi;
      spin.current.vx = dx * k;
      spin.current.vy = dy * k;
    };

    const onUp = (e: PointerEvent) => {
      if (!dragging) return;
      dragging = false;
      canvas.releasePointerCapture(e.pointerId);

      if (moved > CLICK_SLOP) {
        // A real drag: keep coasting unless something is selected.
        if (selectedRef.current) setSelected(null);
        else spin.current.auto = false;
        return;
      }

      spin.current.vx = 0;
      spin.current.vy = 0;
      const rect = canvas.getBoundingClientRect();
      const px = e.clientX - rect.left;
      const py = e.clientY - rect.top;

      // Markers win over countries — they are the smaller, more deliberate target.
      for (const program of PROGRAMS) {
        const coords = PROGRAM_COORDS[program.id];
        if (!coords) continue;
        const p = project(coords[0], coords[1]);
        if (!p.front || Math.hypot(p.x - size / 2, p.y - size / 2) > radius()) continue;
        if (Math.hypot(p.x - px, p.y - py) < 14) {
          setSelected({ ...frameCountry(world, coords[0], coords[1]), program });
          return;
        }
      }

      const hit = unproject(px, py);
      if (!hit || !world) {
        setSelected(null);
        spin.current.auto = true;
        return;
      }
      for (const land of world) {
        if (land.rings.some((ring) => pointInRing(ring, hit.lon, hit.lat))) {
          setSelected({ ...frameCountry(world, hit.lon, hit.lat), at: hit });
          return;
        }
      }
      setSelected(null);
      spin.current.auto = true;
    };

    canvas.addEventListener("pointerdown", onDown);
    canvas.addEventListener("pointermove", onMove);
    canvas.addEventListener("pointerup", onUp);
    canvas.addEventListener("pointercancel", onUp);

    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      canvas.removeEventListener("pointerdown", onDown);
      canvas.removeEventListener("pointermove", onMove);
      canvas.removeEventListener("pointerup", onUp);
      canvas.removeEventListener("pointercancel", onUp);
    };
  }, [world, onPickProgram]);

  const t = copy.quack.globe;
  const country = selected?.program?.country ?? (selected ? countryRu(selected.country) : null);
  const here = selected
    ? PROGRAMS.filter((p) => p.country === country)
    : [];

  return (
    <div className={styles.globe} data-aura>
      <canvas ref={canvasRef} className={styles.canvas} aria-label={t.label} role="img" />

      <div className={styles.card} data-open={Boolean(selected)}>
        {selected ? (
          <>
            <p className={styles.cardCountry}>{country}</p>
            {selected.program ? (
              <>
                <p className={styles.cardTitle}>{selected.program.university}</p>
                <p className={styles.cardLine}>
                  {selected.program.city} · {selected.program.program}
                </p>
                <p className={styles.cardWhere}>
                  €{selected.program.costEur.toLocaleString("ru-RU")}
                  {copy.quack.uni.perYear} · {t.deadline} {selected.program.deadline}
                </p>
              </>
            ) : (
              <>
                <p className={styles.cardLine}>
                  {here.length > 0 ? `${t.programsHere}: ${here.map((p) => p.city).join(", ")}` : t.noPrograms}
                </p>
                {selected.at && <p className={styles.cardWhere}>{whereIs(selected.at.lon, selected.at.lat)}</p>}
              </>
            )}
            <button type="button" className={styles.cardClose} onClick={() => setSelected(null)}>
              {t.back}
            </button>
          </>
        ) : (
          <p className={styles.cardHint}>{world ? t.hint : t.loading}</p>
        )}
      </div>
    </div>
  );
}
