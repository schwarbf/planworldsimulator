import { IsoBox } from "./IsoBox";
import { pts, shade } from "./iso";

export interface VehicleProps {
  x: number;
  y: number;
  kind?: "truck" | "car" | "ship";
  /** Cab, body or container colour. */
  color?: string;
  /** Driving direction: along u (down-right) or along v (down-left). */
  dir?: "u" | "v";
  /** Drive toward −u / −v instead (cab at the back end). */
  reverse?: boolean;
  scale?: number;
}

const CONTAINERS = ["#FF6B4A", "#5B7FD6", "#FFB547"];

/** Truck (white box + coloured cab), car or container ship centred on (x, y). */
export function Vehicle({ x, y, kind = "truck", color = "#FF6B4A", dir = "u", reverse = false, scale = 1 }: VehicleProps) {
  // Lay out along u, then mirror for v (swaps u and v: x → −x).
  const flip = dir === "v" ? " scale(-1 1)" : "";
  let body;
  if (kind === "truck") {
    const cargo = <IsoBox key="cargo" x={reverse ? 2 : -2} y={reverse ? 1 : -1} w={12} d={8} h={9} z0={1} color="#FFFFFF" top="#F7F4EE" stroke="#E2DACB" />;
    const cab = <IsoBox key="cab" x={reverse ? -7 : 7} y={reverse ? -3.5 : 3.5} w={6} d={8} h={7} z0={1} color={color} />;
    // Draw the part further back (smaller u) first.
    body = <>{reverse ? [cab, cargo] : [cargo, cab]}</>;
  } else if (kind === "car") {
    body = (
      <>
        <IsoBox x={0} y={0} w={12} d={7} h={4} z0={1} color={color} />
        <IsoBox x={0} y={0} w={6} d={6} h={3} z0={5} color={shade(color, 1.4)} />
      </>
    );
  } else {
    const hull = [[-26, -8], [18, -8], [30, 0], [18, 8], [-26, 8]].map(([u, v]) => [u - v, (u + v) / 2] as [number, number]);
    body = (
      <>
        <polygon points={pts(hull)} fill="#2E3A59" />
        <polygon points={pts(hull.map(([px, py]) => [px * 0.92, py * 0.92 - 3]))} fill="#3F4D70" />
        {CONTAINERS.map((c, k) => (
          <IsoBox key={k} x={(-16 + k * 12)} y={(-16 + k * 12) / 2 - 3} w={10} d={11} h={6} color={k === 0 ? color : c} />
        ))}
      </>
    );
  }
  return <g transform={`translate(${x} ${y}) scale(${scale})${flip}`}>{body}</g>;
}
