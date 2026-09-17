"use client";

import { useLayoutEffect, useRef, useState } from "react";
import { day, formatShort, TODAY, type ForecastPoint } from "./prepData";
import styles from "./prep.module.css";

type Props = { points: ForecastPoint[]; testDate: Date; forecast: Date };

const H = 220;
const PAD = { top: 18, right: 16, bottom: 28, left: 36 };

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(600);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setWidth(Math.max(280, entry.contentRect.width)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return [ref, width] as const;
}

/** Readiness over time: actual line, dashed forecast to 100%, today and the test date marked. */
export function ForecastChart({ points, testDate, forecast }: Props) {
  const [wrapRef, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);

  const start = day(9, 1).getTime();
  const end = Math.max(testDate.getTime(), forecast.getTime()) + 5 * 86_400_000;
  const x = (d: Date) => PAD.left + ((d.getTime() - start) / (end - start)) * (width - PAD.left - PAD.right);
  const y = (v: number) => PAD.top + (1 - v / 100) * (H - PAD.top - PAD.bottom);

  const actual = points.filter((p) => p.kind === "actual");
  const todayPoint = actual[actual.length - 1];
  const future = [todayPoint, ...points.filter((p) => p.kind === "forecast")];
  const line = (list: ForecastPoint[]) => list.map((p, i) => `${i ? "L" : "M"}${x(p.date).toFixed(1)},${y(p.value).toFixed(1)}`).join(" ");
  const area = `${line(actual)} L${x(todayPoint.date)},${y(0)} L${x(actual[0].date)},${y(0)} Z`;

  const months = [day(9, 1), day(10, 1), day(11, 1)];
  const late = forecast > testDate;

  const onMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const box = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - box.left) / box.width) * width;
    let best = 0;
    points.forEach((p, i) => {
      if (Math.abs(x(p.date) - px) < Math.abs(x(points[best].date) - px)) best = i;
    });
    setHover(best);
  };

  const hovered = hover === null ? null : points[hover];

  return (
    <div className={styles.chart} ref={wrapRef}>
      <svg
        width={width}
        height={H}
        viewBox={`0 0 ${width} ${H}`}
        role="img"
        aria-label={`Готовность сейчас ${todayPoint.value}%, прогноз 100% к ${formatShort(forecast)}, тест ${formatShort(testDate)}`}
        onPointerMove={onMove}
        onPointerLeave={() => setHover(null)}
      >
        {[0, 50, 100].map((v) => (
          <g key={v}>
            <line className={styles.grid} x1={PAD.left} x2={width - PAD.right} y1={y(v)} y2={y(v)} />
            <text className={styles.axisText} x={PAD.left - 8} y={y(v) + 4} textAnchor="end">
              {v}%
            </text>
          </g>
        ))}
        {months.map((m) => (
          <text key={m.getTime()} className={styles.axisText} x={x(m)} y={H - 8} textAnchor="start">
            {formatShort(m).replace(/^\d+ /, "")}
          </text>
        ))}

        <path className={styles.chartArea} d={area} />
        <path className={styles.chartLine} d={line(actual)} />
        <path className={`${styles.chartLine} ${styles.chartForecast}`} d={line(future)} />

        {/* Test date */}
        <line className={styles.testLine} x1={x(testDate)} x2={x(testDate)} y1={PAD.top - 6} y2={H - PAD.bottom} />
        <text className={styles.markerText} x={x(testDate) - 6} y={H - PAD.bottom - 8} textAnchor="end">
          тест {formatShort(testDate)}
        </text>

        {/* Today and forecast */}
        <line className={styles.todayLine} x1={x(TODAY)} x2={x(TODAY)} y1={PAD.top} y2={H - PAD.bottom} />
        <circle className={styles.chartDot} cx={x(todayPoint.date)} cy={y(todayPoint.value)} r={5} />
        <text className={styles.markerText} x={x(TODAY) + 8} y={y(todayPoint.value) + 18}>
          сегодня {todayPoint.value}%
        </text>
        <circle className={`${styles.chartDot} ${late ? styles.chartDotLate : ""}`} cx={x(forecast)} cy={y(100)} r={5} />

        {hovered && (
          <g pointerEvents="none">
            <line className={styles.crosshair} x1={x(hovered.date)} x2={x(hovered.date)} y1={PAD.top} y2={H - PAD.bottom} />
            <circle className={styles.hoverDot} cx={x(hovered.date)} cy={y(hovered.value)} r={6} />
          </g>
        )}
      </svg>

      {hovered && (
        <div
          className={styles.tooltip}
          style={{ left: Math.min(width - 150, Math.max(0, x(hovered.date) - 60)), top: Math.max(0, y(hovered.value) - 58) }}
        >
          <strong>{hovered.value}%</strong>
          <span>
            {formatShort(hovered.date)} · {hovered.kind === "actual" ? "факт" : "прогноз"}
          </span>
        </div>
      )}

      <table className={styles.srOnly}>
        <caption>Готовность по датам</caption>
        <tbody>
          {points.map((p) => (
            <tr key={p.date.getTime()}>
              <td>{formatShort(p.date)}</td>
              <td>{p.value}%</td>
              <td>{p.kind === "actual" ? "факт" : "прогноз"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
