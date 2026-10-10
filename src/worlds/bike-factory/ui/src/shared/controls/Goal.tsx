import { Bar } from "../primitives/Bar";
import { Card } from "../primitives/Card";
import type { ControlsModel } from "../types";

/** Goal text and its progress bars. */
export function Goal({ goal }: { goal: ControlsModel["goal"] }) {
  return (
    <Card>
      <span className="caps">Goal</span>
      <span className="title">{goal.text}</span>
      {goal.bars.map((b) => (
        <div key={b.label} className="insp__progress">
          <div className="between">
            <span className="muted">{b.label}</span>
            <span className="stat__value">{b.value}</span>
          </div>
          <Bar pct={b.pct} tone={b.tone} tick={b.tick} />
        </div>
      ))}
    </Card>
  );
}
