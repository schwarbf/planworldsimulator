import { useEffect, useState } from "react";
import { agentLook, lastRun, startAgent, stopAgent, type AgentInfo, type LastRun, type Play } from "../../harness";
import { Card } from "../primitives/Card";
import { Chip } from "../primitives/Chip";
import { Icon } from "../primitives/Icon";
import type { ControlsModel } from "../types";
import { RobotBadge } from "./AgentCursor";

/** How a run ended (`stopped_by` from the harness), for "Gemini Flash <…>. Your turn." */
const ENDED: Record<string, string> = {
  stopped: "was stopped",
  agent: "finished its turn",
  done: "played to the end",
  limit: "ran out of budget",
  timeout: "hit the time cap",
  error: "failed",
};

const W = 220;
const H = 64;
const PAD = 6;

interface AgentPanelProps {
  agent: ControlsModel["agent"];
  /** Who plays now (`state.play`). */
  play: Play;
  /** Agents from the harness; `offline` while `harness serve` is not running. */
  agents: AgentInfo[];
  offline: boolean;
  /** Current week; from week 2 on the agent continues the player's game. */
  week: number;
  /** After start/stop: refresh the state; `error` when the harness refused. */
  onChanged: (error?: string) => void;
}

/** Agent picker with Start / Stop & take over, experiment score chart, current hypothesis and policy code. */
export function AgentPanel({ agent, play, agents, offline, week, onChanged }: AgentPanelProps) {
  const playing = play.mode === "agent";
  const [choice, setChoice] = useState("");
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState<LastRun | null>(null);
  const selected = choice || play.agent || agents[0]?.name || "";
  const look = agentLook(agents, playing ? play.agent : selected);

  // When a run ends (stopped, done, out of budget, failed), show how.
  useEffect(() => {
    if (!playing && !offline) void lastRun().then(setLast);
  }, [playing, offline]);

  // One line, so the panel keeps its height (the narrator card sits below it).
  const ended = offline
    ? "Run `pixi run harness serve` to let an agent play."
    : last
      ? `${agentLook(agents, last.agent).label} ${ENDED[last.stopped_by] ?? last.stopped_by}` +
        `${last.agent_steps != null ? ` after ${last.agent_steps} weeks` : ""}${last.error ? ` (${last.error})` : ""}. Your turn.`
      : null;

  const toggle = async () => {
    setBusy(true);
    const sent = playing ? await stopAgent() : await startAgent(selected);
    setBusy(false);
    onChanged(sent.ok ? undefined : sent.error);
  };

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
      <div className="agentpick" style={{ ["--agent" as string]: look.color }}>
        <label className="agentpick__select">
          <RobotBadge color={look.color} size={20} />
          <select
            aria-label="Agent"
            value={playing ? play.agent ?? "" : selected}
            disabled={playing || offline || busy || agents.length === 0}
            onChange={(e) => setChoice(e.target.value)}
          >
            {agents.length === 0 && <option value="">{offline ? "Harness offline" : "No agents"}</option>}
            {agents.map((a) => <option key={a.name} value={a.name}>{a.label}</option>)}
          </select>
        </label>
        {playing ? (
          <button className="btn agentpick__stop" disabled={busy} onClick={() => void toggle()}>
            <Icon name="pause" size={12} />
            Stop
          </button>
        ) : (
          <button className="btn agentpick__start" disabled={busy || offline || !selected} onClick={() => void toggle()}>
            <Icon name="play" size={12} />
            {last || week > 1 ? "Continue" : "Start"}
          </button>
        )}
      </div>
      {!playing && ended && <div className="muted agent__hint" title={ended}>{ended}</div>}
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
