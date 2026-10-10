// Page layout around the world view. Same in every world; do not edit per world.
import { useCallback, useState } from "react";
import { sendAction, useWorldState } from "./api";
import { ActionDock } from "./shared/controls/ActionDock";
import { AgentPanel } from "./shared/controls/AgentPanel";
import { Brand } from "./shared/controls/Brand";
import { Discoveries } from "./shared/controls/Discoveries";
import { Goal } from "./shared/controls/Goal";
import { Inspector } from "./shared/controls/Inspector";
import { StoryToast } from "./shared/controls/StoryToast";
import { TopBar } from "./shared/controls/TopBar";
import type { OnAction } from "./shared/types";
import { mockState, toControls, WorldView } from "./World";

export default function App() {
  const state = useWorldState(mockState);
  // null = the world's default selection.
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const model = toControls(state, selectedId);
  const onAction: OnAction = useCallback((id, args) => {
    void sendAction(id, { ...args, ...(selectedId ? { target: selectedId } : {}) });
  }, [selectedId]);

  return (
    <div className="app">
      <div className="app__glow" />
      <div className="app__brand"><Brand brand={model.brand} /></div>
      <div className="app__top">
        <TopBar topBar={model.topBar} />
        {model.story && <StoryToast story={model.story} />}
      </div>
      <div className="app__world">
        <WorldView state={state} selectedId={selectedId} onSelect={setSelectedId} />
      </div>
      <div className="app__left">
        {model.inspector && <Inspector key={model.inspector.title} model={model.inspector} onAction={onAction} />}
        <Discoveries discoveries={model.discoveries} />
      </div>
      <div className="app__right">
        <Goal goal={model.goal} />
        <AgentPanel agent={model.agent} onAction={onAction} />
      </div>
      <div className="app__dock"><ActionDock dock={model.dock} onAction={onAction} /></div>
    </div>
  );
}
