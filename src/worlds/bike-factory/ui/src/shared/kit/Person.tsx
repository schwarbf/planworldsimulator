/** Worker figure with a yellow hard hat, standing on (x, y). */
export function Person({ x, y, color = "#5B7FD6", skin = "#F2C6A0", scale = 1 }: { x: number; y: number; color?: string; skin?: string; scale?: number }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${scale})`}>
      <ellipse cx={0} cy={0} rx={4} ry={2} fill="#000" opacity={0.12} />
      <rect x={-3} y={-11} width={6} height={10} rx={2.5} fill={color} />
      <circle cx={0} cy={-14} r={3} fill={skin} />
      <path d="M-3.6 -14.6a3.6 3.6 0 017.2 0z" fill="#FFC93C" />
    </g>
  );
}
