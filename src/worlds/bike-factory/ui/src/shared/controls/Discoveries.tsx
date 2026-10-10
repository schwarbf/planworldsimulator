import { Card } from "../primitives/Card";
import { Icon } from "../primitives/Icon";
import type { ControlsModel } from "../types";

/** Found and still-hidden rules of the world. */
export function Discoveries({ discoveries }: { discoveries: ControlsModel["discoveries"] }) {
  const { total, found, hidden } = discoveries;
  return (
    <Card>
      <div className="between">
        <span className="title">Discoveries</span>
        <span className="dots">
          {Array.from({ length: total }, (_, k) => <i key={k} className={k < found.length ? "on" : undefined} />)}
        </span>
      </div>
      <div className="muted">{found.length} of {total} hidden rules found. Experiment to find the rest.</div>
      {found.map((r) => (
        <div key={r} className="rule rule--found">
          <span style={{ color: "var(--mint)", display: "flex" }}><Icon name="check" size={16} /></span>
          <span>{r}</span>
        </div>
      ))}
      {hidden.map((hint, k) => (
        <div key={k} className="rule rule--hidden">
          <span className="rule__q">?</span>
          <span>{hint ?? "Hidden rule"}</span>
        </div>
      ))}
    </Card>
  );
}
