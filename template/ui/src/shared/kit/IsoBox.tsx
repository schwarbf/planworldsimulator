import { pts, shade, type Pt } from "./iso";

export interface IsoBoxProps {
  /** Screen point of the footprint centre at ground level. */
  x: number;
  y: number;
  /** Size along u (down-right), along v (down-left), height. */
  w: number;
  d: number;
  h: number;
  color: string;
  /** Top face colour (default: color lightened 1.3). */
  top?: string;
  /** Lift above the ground. */
  z0?: number;
  stroke?: string;
}

/** Local projector for a box footprint centred on (x, y). */
export const local = (x: number, y: number) => (u: number, v: number, z: number): Pt => [x + u - v, y + (u + v) / 2 - z];

/** Shaded isometric box: left face = color, right face darker, top lighter. */
export function IsoBox({ x, y, w, d, h, color, top, z0 = 0, stroke }: IsoBoxProps) {
  const p = local(x, y);
  const a = w / 2, b = d / 2, z1 = z0 + h;
  const left = [p(-a, b, z0), p(a, b, z0), p(a, b, z1), p(-a, b, z1)];
  const right = [p(a, -b, z0), p(a, b, z0), p(a, b, z1), p(a, -b, z1)];
  const roof = [p(-a, -b, z1), p(a, -b, z1), p(a, b, z1), p(-a, b, z1)];
  const s = stroke ? { stroke, strokeWidth: 0.6, strokeLinejoin: "round" as const } : {};
  return (
    <g>
      {h > 0 && <polygon points={pts(left)} fill={color} {...s} />}
      {h > 0 && <polygon points={pts(right)} fill={shade(color, 0.8)} {...s} />}
      <polygon points={pts(roof)} fill={top ?? shade(color, 1.3)} {...s} />
    </g>
  );
}
