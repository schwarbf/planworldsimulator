import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { agentLook, getPace, lastRun, setPace, startAgent, stopAgent, type AgentInfo, type LastRun, type Play } from "../../harness";
import { Card } from "../primitives/Card";
import { Chip } from "../primitives/Chip";
import { Icon } from "../primitives/Icon";
import type { ControlsModel } from "../types";

/** How a run ended (`stopped_by` from the harness), for "Gemini Flash <…>. Your turn." */
const ENDED: Record<string, string> = {
  stopped: "was stopped",
  agent: "finished its turn",
  done: "played to the end",
  limit: "ran out of budget",
  timeout: "hit the time cap",
  error: "failed",
};

const MAX_PACE = 3; // seconds per tool call at the slow end of the slider
const W = 220;
const H = 48;
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
  /** Read the agent's notes aloud in its own voice. */
  voiceNotes: boolean;
  onVoiceNotes: (on: boolean) => void;
}

/**
 * The agent's calls like a terminal: newest line at the bottom, older ones scroll
 * out at the top (scroll up to read them). Sticks to the bottom unless scrolled up.
 */
function Terminal({ text }: { text: string }) {
  const ref = useRef<HTMLPreElement | null>(null);
  const stick = useRef(true);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const toBottom = () => { if (stick.current) el.scrollTop = el.scrollHeight; };
    toBottom();
    if (typeof ResizeObserver === "undefined") return; // e.g. jsdom in tests
    const watch = new ResizeObserver(toBottom); // the panel gives it more or less room
    watch.observe(el);
    return () => watch.disconnect();
  }, [text]);
  return (
    <pre
      ref={ref}
      className="code code--term"
      onScroll={(e) => {
        const el = e.currentTarget;
        stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 8;
      }}
    >
      {text}
    </pre>
  );
}

/** Agent picker with Start / Stop & take over, experiment score chart, current hypothesis and policy code. */
export function AgentPanel({ agent, play, agents, offline, week, onChanged, voiceNotes, onVoiceNotes }: AgentPanelProps) {
  const playing = play.mode === "agent";
  const [choice, setChoice] = useState("");
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState<LastRun | null>(null);
  const [pace, setPaceState] = useState<number | null>(null);

  useEffect(() => {
    if (!offline) void getPace().then(setPaceState);
  }, [offline]);
  const onPace = (seconds: number) => {
    setPaceState(seconds);
    void setPace(seconds);
  };
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
          <i className="agentpick__dot" />
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
      {pace !== null && (
        <label className="agent__speed" style={{ ["--agent" as string]: look.color }} title="Pause before each agent action">
          Speed
          <input type="range" min={0} max={MAX_PACE} step={0.25} value={MAX_PACE - pace}
            onChange={(e) => onPace(MAX_PACE - Number(e.target.value))} aria-label="Agent speed" />
          <b>{pace === 0 ? "max" : `${pace.toFixed(2).replace(/0$/, "")} s/step`}</b>
        </label>
      )}
      <label className="agent__toggle" style={{ ["--agent" as string]: look.color }} title="Reads the agent's newest note aloud in its own voice">
        <input type="checkbox" checked={voiceNotes} onChange={(e) => onVoiceNotes(e.target.checked)} />
        <i className="agent__switch" />
        Voice notes
      </label>
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
      <Terminal text={agent.code} />
    </Card>
  );
}
