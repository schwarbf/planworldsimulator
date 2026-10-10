import { IsoBox, local } from "./IsoBox";
import { pts, shade } from "./iso";

export interface BuildingProps {
  x: number;
  y: number;
  w: number;
  d: number;
  h: number;
  color: string;
  /** Roof colour: a flat box (half size, 6 high), or a gable roof with `gable`. */
  roof?: string;
  gable?: boolean;
  chimney?: boolean;
  windows?: boolean;
  z0?: number;
  /** Object id the agent cursor moves to (`data-target="map:<id>"`). */
  target?: string;
}

const CREAM = "#FFF8EC";

/** Box building with windows on both visible faces, optional roof and chimney. */
export function Building({ x, y, w, d, h, color, roof, gable, chimney, windows = true, z0 = 0, target }: BuildingProps) {
  const p = local(x, y);
  const a = w / 2, b = d / 2, top = z0 + h;
  const wins: string[] = [];
  if (windows) {
    const rows = Math.max(1, Math.floor((h - 6) / 13));
    const ww = 5, wh = 6;
    for (let r = 0; r < rows; r++) {
      const zc = top - 8 - r * 13;
      const colsL = Math.max(1, Math.floor((w - 6) / 12));
      for (let c = 0; c < colsL; c++) {
        const uc = -a + ((c + 0.5) * w) / colsL;
        wins.push(pts([p(uc - ww / 2, b, zc - wh / 2), p(uc + ww / 2, b, zc - wh / 2), p(uc + ww / 2, b, zc + wh / 2), p(uc - ww / 2, b, zc + wh / 2)]));
      }
      const colsR = Math.max(1, Math.floor((d - 6) / 12));
      for (let c = 0; c < colsR; c++) {
        const vc = -b + ((c + 0.5) * d) / colsR;
        wins.push(pts([p(a, vc - ww / 2, zc - wh / 2), p(a, vc + ww / 2, zc - wh / 2), p(a, vc + ww / 2, zc + wh / 2), p(a, vc - ww / 2, zc + wh / 2)]));
      }
    }
  }
  const rc = roof ?? shade(color, 0.85);
  const rh = Math.min(w, d) * 0.35;
  return (
    <g data-target={target ? `map:${target}` : undefined}>
      <IsoBox x={x} y={y} w={w} d={d} h={h} z0={z0} color={color} />
      {wins.map((w2, k) => <polygon key={k} points={w2} fill={CREAM} opacity={0.92} />)}
      {roof && !gable && <IsoBox x={x} y={y} w={w / 2} d={d / 2} h={6} z0={top} color={rc} />}
      {gable && (
        <g>
          <polygon points={pts([p(-a, -b, top), p(a, -b, top), p(a, 0, top + rh), p(-a, 0, top + rh)])} fill={shade(rc, 1.2)} />
          <polygon points={pts([p(a, -b, top), p(a, b, top), p(a, 0, top + rh)])} fill={shade(color, 0.8)} />
          <polygon points={pts([p(-a, 0, top + rh), p(a, 0, top + rh), p(a, b, top), p(-a, b, top)])} fill={rc} />
        </g>
      )}
      {chimney && (
        <g>
          <IsoBox x={x + (-a / 2 + b / 2)} y={y + (-a / 2 - b / 2) / 2} w={7} d={7} h={16} z0={top} color={shade(color, 0.7)} />
          <circle className="pulse" cx={x + (-a / 2 + b / 2) + 3} cy={y + (-a / 2 - b / 2) / 2 - top - 24} r={5} fill="#fff" opacity={0.8} />
          <circle className="pulse" cx={x + (-a / 2 + b / 2) + 8} cy={y + (-a / 2 - b / 2) / 2 - top - 33} r={4} fill="#fff" opacity={0.6} style={{ animationDelay: "0.5s" }} />
        </g>
      )}
    </g>
  );
}

/** Height of the drawn building including its roof, for placing a Hud above it. */
export function buildingTop({ h, w, d, roof, gable, chimney, z0 = 0 }: Pick<BuildingProps, "h" | "w" | "d" | "roof" | "gable" | "chimney" | "z0">): number {
  const extra = gable ? Math.min(w, d) * 0.35 : roof ? 6 : 0;
  return z0 + h + Math.max(extra, chimney ? 30 : 0);
}
