import type { ReactNode } from "react";
import type { Tone } from "../types";

export function Chip({ children, tone = "muted" }: { children: ReactNode; tone?: Tone }) {
  return <span className={`chip tone-${tone}`}>{children}</span>;
}
