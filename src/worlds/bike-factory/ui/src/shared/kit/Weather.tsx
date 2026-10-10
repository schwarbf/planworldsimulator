import { useSvgId } from "./iso";

/** Soft white cloud (three blurred puffs); also used over fog tiles. */
export function Cloud({ x, y, scale = 1, color = "#FFFFFF", opacity = 0.85 }: { x: number; y: number; scale?: number; color?: string; opacity?: number }) {
  const blur = useSvgId("cloud-blur");
  return (
    <g transform={`translate(${x} ${y}) scale(${scale})`} opacity={opacity} pointerEvents="none">
      <defs>
        <filter id={blur} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="3" />
        </filter>
      </defs>
      <g filter={`url(#${blur})`} fill={color}>
        <ellipse cx={-14} cy={2} rx={16} ry={9} />
        <ellipse cx={4} cy={-4} rx={18} ry={12} />
        <ellipse cx={18} cy={3} rx={14} ry={8} />
      </g>
    </g>
  );
}

/** Sun with rays. */
export function Sun({ x, y, r = 14 }: { x: number; y: number; r?: number }) {
  return (
    <g transform={`translate(${x} ${y})`} pointerEvents="none">
      {Array.from({ length: 8 }, (_, k) => (
        <line key={k} x1={0} y1={-r - 4} x2={0} y2={-r - 10} stroke="#FFC93C" strokeWidth={3} strokeLinecap="round" transform={`rotate(${k * 45})`} />
      ))}
      <circle r={r} fill="#FFC93C" />
    </g>
  );
}

/** Grey storm clouds with a flashing lightning bolt. */
export function Storm({ x, y, scale = 1 }: { x: number; y: number; scale?: number }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${scale})`} pointerEvents="none">
      <path className="pulse" d="M2 6l-8 14h7l-5 13 13-18h-7l5-9z" fill="#FFC93C" stroke="#E0A400" strokeWidth={1} />
      <Cloud x={0} y={0} color="#8E96A6" opacity={0.95} />
      <Cloud x={-22} y={6} scale={0.7} color="#A7AEBB" opacity={0.9} />
    </g>
  );
}
