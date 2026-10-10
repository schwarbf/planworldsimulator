import type { CSSProperties, ReactNode } from "react";

/**
 * World view frame: keeps the SVG and the HTML overlay (Hud pills) at the same
 * aspect ratio, so `toPercent(x, y, width, height)` lines up with SVG coordinates.
 */
export function Stage({ width, height, children, overlay }: { width: number; height: number; children: ReactNode; overlay?: ReactNode }) {
  return (
    <div className="world">
      <div className="world__stage" style={{ "--vw": width, "--vh": height } as CSSProperties}>
        <svg viewBox={`0 0 ${width} ${height}`}>{children}</svg>
        {overlay}
      </div>
    </div>
  );
}
