import type { ReactNode } from "react";
import { Bar } from "./Bar";

interface HudProps {
  /** Position in percent of the world view (from kit `toPercent`). */
  x: number;
  y: number;
  label: string;
  level?: number | string;
  pct?: number;
  color?: string;
  tag?: ReactNode;
  selected?: boolean;
  alert?: boolean;
  onClick?: () => void;
}

/** Map label pill shown above an object in the world view. */
export function Hud({ x, y, label, level, pct, color, tag, selected, alert, onClick }: HudProps) {
  const cls = ["hud", selected && "hud--selected", alert && "hud--alert"].filter(Boolean).join(" ");
  return (
    <div className={cls} style={{ left: `${x}%`, top: `${y}%` }} onClick={onClick}>
      {level != null && <span className="hud__lv">{level}</span>}
      <span>{label}</span>
      {pct != null && !alert && <Bar pct={pct} color={color} />}
      {tag}
    </div>
  );
}
