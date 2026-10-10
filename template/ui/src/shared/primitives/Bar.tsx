import type { Tone } from "../types";

const fill: Record<Tone, string> = {
  ink: "var(--ink)", coral: "var(--coral)", mint: "var(--mint)",
  amber: "var(--amber)", violet: "var(--violet)", muted: "var(--dim)",
};

/** Progress bar; `color` overrides the tone, `tick` marks a target (0–1). */
export function Bar({ pct, tone = "ink", color, tick, height }: { pct: number; tone?: Tone; color?: string; tick?: number; height?: number }) {
  return (
    <div className="bar" style={height ? { height } : undefined}>
      <div className="bar__fill" style={{ width: `${Math.max(2, Math.min(1, pct) * 100)}%`, background: color ?? fill[tone] }} />
      {tick != null && <div className="bar__tick" style={{ left: `calc(${tick * 100}% - 1px)` }} />}
    </div>
  );
}
