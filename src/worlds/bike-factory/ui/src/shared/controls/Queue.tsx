import { Card } from "../primitives/Card";
import type { QueuedAction } from "../types";

/** This step's queued actions; each can be removed before Play. */
export function Queue({ queued, onRemove }: { queued: QueuedAction[]; onRemove: (index: number) => void }) {
  return (
    <Card>
      <div className="between">
        <span className="title">Queued</span>
        <span className="caps">{queued.length} this week</span>
      </div>
      {queued.length === 0 && <div className="muted">No actions queued. They run when you press Play.</div>}
      {queued.map(({ action, ...args }, k) => (
        <div key={`${k}-${action}`} className="queued">
          <span className="queued__verb">{action}</span>
          <span className="queued__args">{Object.values(args).join(" · ")}</span>
          <button className="queued__x" aria-label={`Remove ${action}`} title="Remove" onClick={() => onRemove(k)}>×</button>
        </div>
      ))}
    </Card>
  );
}
