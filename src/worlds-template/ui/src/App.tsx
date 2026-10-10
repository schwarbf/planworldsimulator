// Page layout around the world view. Same in every world; do not edit per world.
import { memo, useCallback, useEffect, useMemo, useState } from "react";
import { resetToLevel, sendAction, unqueue, useWorldState } from "./api";
import { agentLook, stopAgent, useAgents, type Play } from "./harness";
import { AgentBanner, FrozenLock } from "./shared/controls/AgentBanner";
import { AgentCursor } from "./shared/controls/AgentCursor";
import { ActionDock } from "./shared/controls/ActionDock";
import { AgentPanel } from "./shared/controls/AgentPanel";
import { Brand } from "./shared/controls/Brand";
import { Discoveries } from "./shared/controls/Discoveries";
import { Goal } from "./shared/controls/Goal";
import { Inspector } from "./shared/controls/Inspector";
import { Narrator } from "./shared/controls/Narrator";
import { Queue } from "./shared/controls/Queue";
import { StoryToast } from "./shared/controls/StoryToast";
import { TopBar } from "./shared/controls/TopBar";
import type { OnAction, QueuedAction, ScoreInfo } from "./shared/types";
import { mockState, toControls, WorldView } from "./World";

// The SVG world is the heaviest part; redraw it only when its props change.
const MemoWorldView = memo(WorldView);
const ERROR_MS = 3000;
const NOBODY: Play = { mode: "you", agent: null };
const ignore: OnAction = () => {};

export default function App() {
  const [state, refresh] = useWorldState(mockState);
  // null = the world's default selection.
  const [selectedId, setSelectedId] = useState<string | null>(null);
  // Dock verb shown as active right away, before the server confirms it.
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [narratorOpen, setNarratorOpen] = useState(false);
  const model = useMemo(() => toControls(state, selectedId), [state, selectedId]);
  const queued = (state as { queued?: QueuedAction[] }).queued ?? [];
  const score = (state as { score?: ScoreInfo }).score;

  // Agent playing (decision 0007): who plays, the harness's agents, frozen controls.
  const play = (state as { play?: Play }).play ?? NOBODY;
  const playing = play.mode === "agent";
  const { agents, offline } = useAgents();
  const look = agentLook(agents, play.agent);

  // `?level=N` (from the website's Play links) starts the world at that difficulty.
  useEffect(() => {
    const level = Number(new URLSearchParams(window.location.search).get("level"));
    if (Number.isInteger(level) && level >= 1 && level <= 3) {
      void resetToLevel(level).then((sent) => {
        if (!sent.ok) setError(sent.error ?? "Could not select difficulty");
        return refresh();
      });
    }
  }, [refresh]);
  useEffect(() => setPending(null), [model.dock.active]);
  useEffect(() => {
    if (!error) return;
    const timer = setTimeout(() => setError(null), ERROR_MS);
    return () => clearTimeout(timer);
  }, [error]);

  const run = useCallback(async (id: string, args?: Record<string, unknown>) => {
    const sent = await sendAction(id, { ...args, ...(selectedId ? { target: selectedId } : {}) });
    if (!sent.ok) setError(sent.error ?? "Action rejected");
    await refresh();
    return sent.ok;
  }, [selectedId, refresh]);

  const onAction: OnAction = useCallback((id, args) => void run(id, args), [run]);

  // A dock verb queues that action for the selection, with the inspector's default amount.
  const primary = model.inspector?.primary;
  const verbs = model.dock.verbs;
  const onDock: OnAction = useCallback((id, args) => {
    if (!verbs.some((v) => v.id === id)) return onAction(id, args);
    setPending(id);
    const defaults = primary?.id === id ? { amount: primary.amount } : {};
    void run(id, { ...defaults, ...args }).then((ok) => { if (!ok) setPending(null); });
  }, [verbs, primary, run, onAction]);

  const onRemove = useCallback(async (index: number) => {
    const sent = await unqueue(index);
    if (!sent.ok) setError(sent.error ?? "Could not remove");
    await refresh();
  }, [refresh]);

  const onAgentChanged = useCallback((err?: string) => {
    if (err) setError(err);
    void refresh();
  }, [refresh]);
  const takeOver = useCallback(() => {
    void stopAgent().then((sent) => onAgentChanged(sent.ok ? undefined : sent.error));
  }, [onAgentChanged]);

  const dock = useMemo(() => ({ ...model.dock, active: pending ?? model.dock.active }), [model.dock, pending]);

  return (
    <div className={`app${narratorOpen ? " app--narrator-open" : ""}`}>
      <div className="app__glow" />
      <div className="app__brand"><Brand brand={model.brand} /></div>
      <div className="app__top">
        <TopBar topBar={model.topBar} />
        {error ? (
          <div className="story story--coral" role="alert">
            <span className="story__tag">Not queued</span>
            <span>{error}</span>
          </div>
        ) : model.story && <StoryToast story={model.story} />}
      </div>
      <div className="app__world">
        <MemoWorldView state={state} selectedId={selectedId} onSelect={setSelectedId} />
      </div>
      <div className={`app__left${playing ? " frozen" : ""}`}>
        {playing && <FrozenLock />}
        {model.inspector && <Inspector key={model.inspector.title} model={model.inspector} onAction={playing ? ignore : onAction} />}
        <Queue queued={queued} onRemove={(k) => void onRemove(k)} />
        <Discoveries discoveries={model.discoveries} />
      </div>
      <div className="app__right">
        <Goal goal={model.goal} score={score} />
        <AgentPanel agent={model.agent} play={play} agents={agents} offline={offline} week={score?.week ?? 1} onChanged={onAgentChanged} />
      </div>
      <div className={`app__dock${playing ? " frozen" : ""}`}>
        {playing && <FrozenLock />}
        <ActionDock dock={dock} onAction={playing ? ignore : onDock} />
      </div>
      <div className="app__narrator"><Narrator collapse={playing} onOpen={setNarratorOpen} week={score?.week} /></div>
      {playing && <AgentBanner look={look} timeLabel={model.topBar.timeLabel} onStop={takeOver} />}
      <AgentCursor look={look} active={playing} onTarget={setSelectedId} />
    </div>
  );
}
