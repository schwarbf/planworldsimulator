import { Bar } from "../primitives/Bar";
import { Card } from "../primitives/Card";
import type { ControlsModel, ScoreInfo } from "../types";

/** Goal text, its progress bars, and the current score with how it is computed. */
export function Goal({ goal, score }: { goal: ControlsModel["goal"]; score?: ScoreInfo }) {
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
      {score && (
        <div className="goal__score">
          <div className="between">
            <span className="caps">Score</span>
            <span className="stat__value">
              {score.score.toFixed(2)} <span className="muted">· baseline {score.baseline.toFixed(2)}</span>
            </span>
          </div>
          {score.formula && <div className="muted">{score.formula}</div>}
        </div>
      )}
    </Card>
  );
}
