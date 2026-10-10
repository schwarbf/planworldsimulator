import { pts, type Pt } from "./iso";

/** Route / power / water line: soft glow underlay plus a dashed (animated) stroke. */
export function Flow({ points, color = "#FFFFFF", width = 3, animated = true }: { points: Pt[]; color?: string; width?: number; animated?: boolean }) {
  const p = pts(points);
  return (
    <g pointerEvents="none" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <polyline points={p} stroke={color} strokeWidth={width * 3} opacity={0.3} />
      <polyline points={p} stroke={color} strokeWidth={width} strokeDasharray="8 4" className={animated ? "flow" : undefined} />
    </g>
  );
}
