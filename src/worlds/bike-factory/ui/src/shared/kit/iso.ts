// Isometric projection and tile math for world views.
// Axes: u runs down-right, v runs down-left, z runs up (all in screen pixels).
import { useId } from "react";

export type Pt = [number, number];
export type Projector = (u: number, v: number, z?: number) => Pt;

/** Projector around a screen origin: x = cx + (u − v), y = cy + (u + v)/2 − z. */
export function project(cx: number, cy: number): Projector {
  return (u, v, z = 0) => [cx + (u - v), cy + (u + v) / 2 - z];
}

/** Darken (f < 1) or lighten toward white (f > 1) a #rgb / #rrggbb colour. */
export function shade(hex: string, f: number): string {
  let h = hex.replace("#", "");
  if (h.length === 3) h = h.split("").map((c) => c + c).join("");
  const n = parseInt(h.slice(0, 6), 16);
  const ch = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((c) => {
    const out = f <= 1 ? c * f : c + (255 - c) * (f - 1);
    return Math.round(Math.max(0, Math.min(255, out)));
  });
  return `#${ch.map((c) => c.toString(16).padStart(2, "0")).join("")}`;
}

/** Points array → SVG `points` attribute. */
export function pts(points: Pt[]): string {
  return points.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
}

/** SVG coordinates → percent of the view, for `Hud` placement. */
export function toPercent(x: number, y: number, viewW: number, viewH: number): { x: number; y: number } {
  return { x: (x / viewW) * 100, y: (y / viewH) * 100 };
}

/** Unique id usable in `url(#…)` (React ids contain colons). */
export function useSvgId(prefix: string): string {
  return `${prefix}-${useId().replace(/:/g, "")}`;
}

export interface Grid {
  cx: number;
  cy: number;
  n: number;
  size: number;
  slab: number;
  /** Projector whose z = 0 is the top of the slab. */
  p: Projector;
  /** Iso coordinates (u, v) of the centre of tile (i, j). */
  uv(i: number, j: number): [number, number];
  /** Screen point of the centre of tile (i, j), on top of the slab. */
  at(i: number, j: number): Pt;
  /** The four screen corners of tile (i, j), scaled by `k` (1 = full tile). */
  diamond(i: number, j: number, k?: number): Pt[];
}

/** n × n tile grid whose top-surface centre sits at (cx, cy). */
export function makeGrid({ cx, cy, n, size, slab = 16 }: { cx: number; cy: number; n: number; size: number; slab?: number }): Grid {
  const p = project(cx, cy);
  const uv = (i: number, j: number): [number, number] => [(i - n / 2 + 0.5) * size, (j - n / 2 + 0.5) * size];
  return {
    cx, cy, n, size, slab, p, uv,
    at: (i, j) => p(...uv(i, j)),
    diamond: (i, j, k = 1) => {
      const [u, v] = uv(i, j);
      const s = (size / 2) * k;
      return [p(u - s, v - s), p(u + s, v - s), p(u + s, v + s), p(u - s, v + s)];
    },
  };
}

/** Sort key for painter's order: draw smaller i + j first (back to front). */
export const depth = (i: number, j: number) => i + j;
