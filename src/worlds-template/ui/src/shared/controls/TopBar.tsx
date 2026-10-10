import { Bar } from "../primitives/Bar";
import { Chip } from "../primitives/Chip";
import type { ControlsModel } from "../types";

/** Main number (cash, bill, …), rate chips and time progress. */
export function TopBar({ topBar }: { topBar: ControlsModel["topBar"] }) {
  return (
    <div className="topbar">
      <div className="row">
        <span className="topbar__value">{topBar.value}</span>
        {topBar.chips.map((c) => (
          <Chip key={c.text} tone={c.tone}>{c.text}</Chip>
        ))}
      </div>
      <div className="topbar__time">
        <span>{topBar.timeLabel}</span>
        <Bar pct={topBar.timeProgress} tone="ink" />
      </div>
    </div>
  );
}
