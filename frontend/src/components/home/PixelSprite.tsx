import type { ReactNode } from "react";

export type Palette = Record<string, string>;

/**
 * One <rect> per horizontal run of one colour, so a sprite is a few dozen rects
 * rather than one per pixel. Characters missing from the palette are transparent.
 */
export function pixelRects(map: string[], palette: Palette, key: string): ReactNode[] {
  const rects: ReactNode[] = [];
  map.forEach((row, y) => {
    let x = 0;
    while (x < row.length) {
      const ch = row[x];
      if (!palette[ch]) {
        x++;
        continue;
      }
      let run = 1;
      while (x + run < row.length && row[x + run] === ch) run++;
      rects.push(<rect key={`${key}-${x}-${y}`} x={x} y={y} width={run} height={1} fill={palette[ch]} />);
      x += run;
    }
  });
  return rects;
}

type PixelSpriteProps = {
  map: string[];
  palette: Palette;
  /** Screen pixels per sprite pixel. */
  unit: number;
  className?: string;
  children?: ReactNode;
};

/** A crisp pixel-art sprite drawn at a whole-number scale. Extra SVG goes in `children`. */
export function PixelSprite({ map, palette, unit, className, children }: PixelSpriteProps) {
  const w = map[0].length;
  const h = map.length;
  return (
    <svg
      className={className}
      width={w * unit}
      height={h * unit}
      viewBox={`0 0 ${w} ${h}`}
      shapeRendering="crispEdges"
      aria-hidden="true"
    >
      {pixelRects(map, palette, "p")}
      {children}
    </svg>
  );
}
