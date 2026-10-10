import type { ReactNode } from "react";
import { IsoBox } from "./IsoBox";
import { pts, useSvgId, type Grid } from "./iso";

export type TileKind = "grass" | "path" | "water" | "none";

const TILE = ["#EFE6D2", "#EAE0CA"];
const WATER = ["#94C8E4", "#9FD0EA"];

/** Floating tile island for a grid from `makeGrid`. Children render on top. */
export function IsoIsland({ grid, tileKind, children }: { grid: Grid; tileKind?: (i: number, j: number) => TileKind; children?: ReactNode }) {
  const { cx, cy, n, size, slab } = grid;
  const blur = useSvgId("island-blur");
  const half = (n * size) / 2;
  const tiles: ReactNode[] = [];
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      const kind = tileKind?.(i, j) ?? "grass";
      if (kind === "none") continue;
      const alt = (i + j) % 2;
      const fill = kind === "path" ? "#D5C5A4" : kind === "water" ? WATER[alt] : TILE[alt];
      tiles.push(<polygon key={`${i}-${j}`} points={pts(grid.diamond(i, j))} fill={fill} stroke="#DDD0B5" strokeWidth={0.8} />);
    }
  }
  return (
    <g>
      <defs>
        <filter id={blur} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="18" />
        </filter>
      </defs>
      <ellipse cx={cx} cy={cy + half / 2 + slab + 40} rx={half * 0.85} ry={half * 0.18} fill="#3a2e1a" opacity={0.18} filter={`url(#${blur})`} />
      <ellipse cx={cx} cy={cy} rx={half * 1.15} ry={half * 0.62} fill="#fff" opacity={0.6} filter={`url(#${blur})`} />
      <IsoBox x={cx} y={cy} w={n * size} d={n * size} h={slab} z0={-slab} color="#D9C9A7" top="#EFE6D2" />
      {tiles}
      {children}
    </g>
  );
}
