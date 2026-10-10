import { Card } from "../primitives/Card";
import { Chip } from "../primitives/Chip";
import type { ControlsModel, OnAction } from "../types";

const W = 220;
const H = 64;
const PAD = 6;

/** You/Agent toggle, experiment score chart, current hypothesis and policy code. */
export function AgentPanel({ agent, onAction }: { agent: ControlsModel["agent"]; onAction: OnAction }) {
  const slots = Math.max(2, agent.slots);
  const x = (k: number) => PAD + (k / (slots - 1)) * (W - 2 * PAD);
  const y = (s: number) => H - PAD - Math.max(0, Math.min(1, s)) * (H - 2 * PAD);
  const line = agent.scores.map((s, k) => `${x(k).toFixed(1)},${y(s).toFixed(1)}`).join(" ");

  return (
    <Card>
      <div className="between">
        <span className="row">
          <i className="agent__dot" />
          <span className="title">Agent</span>
        </span>
        <Chip tone="violet">{agent.experiment}</Chip>
      </div>
      <div className="toggle">
        {(["you", "agent"] as const).map((m) => (
          <button key={m} className={agent.mode === m ? "on" : undefined} onClick={() => onAction("mode", { mode: m })}>
            {m === "you" ? "You" : "Agent"}
          </button>
        ))}
      </div>
      <div className="chart">
        <div className="between">
          <span className="caps">Score / experiment</span>
          <span className="muted">baseline {agent.baseline.toFixed(2)}</span>
        </div>
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} preserveAspectRatio="none" aria-hidden>
          <line x1={PAD} x2={W - PAD} y1={y(agent.baseline)} y2={y(agent.baseline)} stroke="var(--dim)" strokeWidth="1.2" strokeDasharray="4 3" />
          <polyline points={line} fill="none" stroke="var(--violet)" strokeWidth="2" strokeLinejoin="round" />
          {agent.scores.map((s, k) => (
            <circle key={k} cx={x(k)} cy={y(s)} r={k === agent.scores.length - 1 ? 3.5 : 2.5} fill="var(--violet)" stroke="#fff" strokeWidth="1" />
          ))}
        </svg>
      </div>
      <div className="insp__col">
        <span className="caps">Now testing</span>
        <span className="agent__now">{agent.now}</span>
      </div>
      <pre className="code">{agent.code}</pre>
    </Card>
  );
}
