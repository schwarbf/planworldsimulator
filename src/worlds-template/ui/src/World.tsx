// [gen] TODO: replace with this world's view and controls config.
// Placeholder so the template runs: one shop on a small island.
// Reference implementation: src/worlds/bike-factory/ui/src/World.tsx
//
// Exports (contract, used by App.tsx):
//   mockState                      plain JSON-like state; same shape as GET /api/state (env.ui_state)
//   toControls(state, selectedId)  state → ControlsModel for the shared controls
//   WorldView({ state, selectedId, onSelect })  the isometric world drawing (use shared/kit)
import { Building, buildingTop } from "./shared/kit/Building";
import { IsoIsland } from "./shared/kit/IsoIsland";
import { Stage } from "./shared/kit/Stage";
import { Tree } from "./shared/kit/Tree";
import { makeGrid, pts, toPercent } from "./shared/kit/iso";
import { Hud } from "./shared/primitives/Hud";
import type { ControlsModel } from "./shared/types";

// ---------- state (must match env.ui_state) ----------

import type { State } from "./WorldState";
export type { State } from "./WorldState";
export { mockState } from "./WorldState";

// ---------- controls ----------

export function toControls(state: State, _selectedId: string | null): ControlsModel {
  return {
    brand: { world: state.world.name, seed: state.world.seed, difficulty: state.world.difficulty },
    topBar: {
      value: `CHF ${state.cash.toLocaleString("en-US")}`,
      chips: [],
      timeLabel: `Week ${state.week} / ${state.weeks}`,
      timeProgress: state.week / state.weeks,
    },
    story: state.story ?? undefined,
    inspector: {
      title: "Shop",
      level: 1,
      subtitle: "The only site · selected",
      progress: { label: "Utilisation", value: `${state.capacity} / ${state.demand}`, pct: Math.min(1, state.capacity / Math.max(1, state.demand)), tone: "mint" },
      stats: [
        { label: "Capacity", value: String(state.capacity) },
        { label: "Demand", value: String(state.demand) },
      ],
      primary: { id: "invest", label: "Invest", icon: "expand", amount: 1, step: 1 },
      actions: [],
    },
    discoveries: state.discoveries,
    goal: {
      text: `Make CHF ${state.target.toLocaleString("en-US")} profit`,
      bars: [{ label: "Profit", value: `CHF ${state.profit.toLocaleString("en-US")}`, pct: state.profit / state.target, tone: "ink" }],
    },
    agent: {
      experiment: `EXP ${state.agent.experiment} / ${state.agent.experiments}`,
      mode: state.agent.mode,
      scores: state.agent.scores,
      baseline: state.agent.baseline,
      slots: state.agent.experiments,
      now: state.agent.now,
      code: state.agent.code,
    },
    dock: {
      verbs: [{ id: "invest", label: "Invest", icon: "expand", key: "Q" }],
      active: state.active ?? "invest",
      unlocked: 1,
      total: 8,
    },
  };
}

// ---------- world view ----------

const VIEW_W = 880;
const VIEW_H = 640;
const grid = makeGrid({ cx: 440, cy: 330, n: 7, size: 48 });
const SHOP = { w: 70, d: 56, h: 44, color: "#5B7FD6", roof: "#3F5FB0" };

export function WorldView({ state, onSelect }: { state: State; selectedId: string | null; onSelect: (id: string) => void }) {
  const [x, y] = grid.at(3, 3);
  const hud = toPercent(x, y - buildingTop(SHOP) - 34, VIEW_W, VIEW_H);
  return (
    <Stage
      width={VIEW_W}
      height={VIEW_H}
      overlay={<Hud x={hud.x} y={hud.y} level={1} label="Shop" pct={Math.min(1, state.capacity / Math.max(1, state.demand))} color={SHOP.color} selected onClick={() => onSelect("shop")} />}
    >
      <IsoIsland grid={grid} tileKind={() => "grass"}>
        <polygon points={pts(grid.diamond(3, 3, 1.5))} fill="none" stroke="var(--ink)" strokeWidth={2} strokeDasharray="6 4" />
        <Tree x={grid.at(1, 2)[0]} y={grid.at(1, 2)[1]} />
        <Tree x={grid.at(2, 5)[0]} y={grid.at(2, 5)[1]} />
        <g className="clickable" onClick={() => onSelect("shop")}>
          <Building x={x} y={y} {...SHOP} target="shop" />
        </g>
        <Tree x={grid.at(5, 4)[0]} y={grid.at(5, 4)[1]} />
      </IsoIsland>
    </Stage>
  );
}
