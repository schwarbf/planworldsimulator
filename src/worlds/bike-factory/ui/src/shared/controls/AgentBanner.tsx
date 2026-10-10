import { Icon } from "../primitives/Icon";
import { RobotBadge, type AgentLook } from "./AgentCursor";

/** "Gemini Flash is playing · week 12 / 52 · Stop & take over", above the frozen dock. */
export function AgentBanner({ look, timeLabel, onStop }: { look: AgentLook; timeLabel: string; onStop: () => void }) {
  return (
    <div className="agentbar" role="status" style={{ ["--agent" as string]: look.color }}>
      <RobotBadge color={look.color} size={24} />
      <span><b>{look.label}</b> is playing · {timeLabel.toLowerCase()}</span>
      <button className="agentbar__stop" onClick={onStop}>
        <Icon name="pause" size={12} />
        Stop &amp; take over
      </button>
    </div>
  );
}

/** Lock badge on a control area while the agent plays (the area gets `frozen`). */
export function FrozenLock() {
  return (
    <span className="frozen__lock" title="The agent is playing" aria-label="Locked while the agent plays">
      <Icon name="lock" size={11} />
    </span>
  );
}
