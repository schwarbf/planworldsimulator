import { IsoBox } from "./IsoBox";

export { Cloud } from "./Weather";

/** Raised fog tile over an unexplored tile; `question` adds a "?". */
export function Fog({ x, y, size, question }: { x: number; y: number; size: number; question?: boolean }) {
  return (
    <g>
      <IsoBox x={x} y={y} w={size} d={size} h={12} color="#CBC3B5" top="#DAD3C7" />
      {question && (
        <text x={x} y={y - 12 + 5} textAnchor="middle" fontFamily="var(--display)" fontWeight={700} fontSize={16} fill="#9C9384">?</text>
      )}
    </g>
  );
}
