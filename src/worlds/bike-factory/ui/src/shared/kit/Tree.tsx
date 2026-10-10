import { IsoBox } from "./IsoBox";
import { shade } from "./iso";

/** Round tree standing on (x, y). `color` is the crown colour. */
export function Tree({ x, y, color = "#5FAE62", scale = 1 }: { x: number; y: number; color?: string; scale?: number }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${scale})`}>
      <ellipse cx={0} cy={1} rx={9} ry={4.5} fill="#000" opacity={0.08} />
      <IsoBox x={0} y={0} w={4} d={4} h={10} color="#8B6A4A" />
      <circle cx={0} cy={-18} r={10} fill={color} />
      <circle cx={-3} cy={-21} r={5} fill={color === "#5FAE62" ? "#8ED07F" : shade(color, 1.35)} />
    </g>
  );
}
