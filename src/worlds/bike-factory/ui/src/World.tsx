// Bike Factory (Medium) — reference World.tsx.
// A generated world writes only this file. It exports:
//   mockState                      plain JSON-like state; same shape as GET /api/state
//   toControls(state, selectedId)  state → ControlsModel for the shared controls
//   WorldView({ state, selectedId, onSelect })  the isometric world drawing
import type { ReactNode } from "react";
import { Building, buildingTop } from "./shared/kit/Building";
import { Flow } from "./shared/kit/Flow";
import { Cloud, Fog } from "./shared/kit/Fog";
import { IsoIsland, type TileKind } from "./shared/kit/IsoIsland";
import { Person } from "./shared/kit/Person";
import { Stage } from "./shared/kit/Stage";
import { Tree } from "./shared/kit/Tree";
import { Vehicle } from "./shared/kit/Vehicle";
import { Storm } from "./shared/kit/Weather";
import { makeGrid, pts, toPercent, type Pt } from "./shared/kit/iso";
import { Chip } from "./shared/primitives/Chip";
import { Hud } from "./shared/primitives/Hud";
import type { ControlsModel, InspectorModel } from "./shared/types";

// ---------- state ----------

type SiteType = "supplier" | "plant" | "assembly" | "warehouse" | "store";

interface Site {
  id: string;
  name: string;
  type: SiteType;
  i: number;
  j: number;
  level: number;
  /** Utilisation / fill shown in the Hud bar (0–1). */
  pct: number;
  stock: number;
  incoming: number;
  leadWeeks: number;
  backlog: number;
  holdingPerWeek: number;
  outOfStock?: boolean;
}

interface Route { from: string; to: string }

export interface State {
  world: { name: string; seed: string; difficulty: string };
  cash: number;
  perDay: number;
  week: number;
  weeks: number;
  sites: Site[];
  routes: Route[];
  /** Unexplored tiles as [i, j]; `true` third entry shows a "?". */
  fog: [number, number, boolean][];
  water: [number, number][];
  trees: [number, number][];
  workers: [number, number][];
  storm?: [number, number];
  story?: { tag: string; text: string; tone: "amber" | "mint" | "coral" };
  discoveries: { total: number; found: string[]; hidden: (string | null)[] };
  goal: { profit: number; target: number; served: number; servedTarget: number };
  agent: { experiment: number; experiments: number; mode: "you" | "agent"; scores: number[]; baseline: number; now: string; code: string };
  dock: { active: string; unlocked: number; total: number };
}

const N = 11;
const fog: [number, number, boolean][] = [];
for (let i = 0; i < N; i++) {
  for (let j = 0; j < N; j++) {
    if ((i >= 7 && j <= 1) || (i <= 1 && j <= 2)) fog.push([i, j, (i === 8 && j === 0) || (i === 10 && j === 1) || (i === 0 && j === 1)]);
  }
}

export const mockState: State = {
  world: { name: "Bike Factory", seed: "4821", difficulty: "Medium" },
  cash: 184220,
  perDay: 1240,
  week: 12,
  weeks: 52,
  sites: [
    { id: "tier2", name: "Tier 2 Supplier", type: "supplier", i: 1, j: 8, level: 2, pct: 0.55, stock: 340, incoming: 0, leadWeeks: 4, backlog: 40, holdingPerWeek: 300 },
    { id: "tier1", name: "Tier 1 Supplier", type: "supplier", i: 4, j: 10, level: 3, pct: 0.7, stock: 180, incoming: 120, leadWeeks: 2, backlog: 0, holdingPerWeek: 450 },
    { id: "components", name: "Components", type: "plant", i: 2, j: 5, level: 3, pct: 0.62, stock: 96, incoming: 80, leadWeeks: 1, backlog: 12, holdingPerWeek: 640 },
    { id: "assembly", name: "Assembly", type: "assembly", i: 5, j: 3, level: 5, pct: 0.81, stock: 48, incoming: 60, leadWeeks: 1, backlog: 0, holdingPerWeek: 900 },
    { id: "warehouse", name: "Warehouse", type: "warehouse", i: 7, j: 6, level: 4, pct: 0.68, stock: 212, incoming: 60, leadWeeks: 2, backlog: 0, holdingPerWeek: 1200 },
    { id: "storeA", name: "Store A", type: "store", i: 9, j: 2, level: 2, pct: 0.74, stock: 38, incoming: 20, leadWeeks: 1, backlog: 0, holdingPerWeek: 180 },
    { id: "storeB", name: "Store B", type: "store", i: 10, j: 6, level: 2, pct: 0, stock: 0, incoming: 20, leadWeeks: 1, backlog: 26, holdingPerWeek: 0, outOfStock: true },
    { id: "storeC", name: "Store C", type: "store", i: 8, j: 9, level: 1, pct: 0.45, stock: 22, incoming: 10, leadWeeks: 1, backlog: 0, holdingPerWeek: 110 },
  ],
  routes: [
    { from: "tier2", to: "tier1" },
    { from: "tier1", to: "components" },
    { from: "components", to: "assembly" },
    { from: "assembly", to: "warehouse" },
    { from: "warehouse", to: "storeA" },
    { from: "warehouse", to: "storeB" },
    { from: "warehouse", to: "storeC" },
  ],
  fog,
  water: [[5, 7], [6, 7], [5, 8], [6, 8]],
  trees: [[0, 4], [0, 7], [1, 10], [3, 1], [4, 1], [6, 0], [6, 10], [10, 9], [10, 10], [3, 7], [10, 3]],
  workers: [[3, 4], [6, 4]],
  storm: [0, 9],
  story: { tag: "WEEK 3", text: "Storms reported near Tier 2. Deliveries feel slower…", tone: "amber" },
  discoveries: {
    total: 3,
    found: ["Store demand peaks every ~8 weeks", "Tier 2 is late after storms (+2 wk)"],
    hidden: ["Store B behaves oddly in winter"],
  },
  goal: { profit: 184220, target: 1_000_000, served: 0.93, servedTarget: 0.95 },
  agent: {
    experiment: 7,
    experiments: 20,
    mode: "agent",
    scores: [0.18, 0.34, 0.29, 0.47, 0.55, 0.6, 0.71],
    baseline: 0.58,
    now: "Smoothed orders at the warehouse — does it calm the bullwhip?",
    code: [
      "def policy(obs):",
      "    demand = obs.stores.demand.mean(weeks=4)",
      "    gap = 2 * demand - obs.warehouse.stock",
      "    return Order(qty=max(0, round(gap, -1)))",
    ].join("\n"),
  },
  dock: { active: "order", unlocked: 4, total: 8 },
};

// ---------- look ----------

const DEFAULT_SELECTED = "warehouse";

interface Look { color: string; w: number; d: number; h: number; roof?: string; gable?: boolean; chimney?: boolean }

const LOOK: Record<string, Look> = {
  tier2: { color: "#8C9AB0", w: 30, d: 28, h: 24, roof: "#6E7C92", gable: true },
  tier1: { color: "#F2967A", w: 30, d: 30, h: 28, roof: "#D9775A" },
  components: { color: "#D9B98C", w: 34, d: 30, h: 28, chimney: true },
  assembly: { color: "#5B7FD6", w: 52, d: 50, h: 42, roof: "#4A6BC0" },
  warehouse: { color: "#FFB547", w: 40, d: 34, h: 30, roof: "#E89A2A" },
  storeA: { color: "#FF6B4A", w: 26, d: 26, h: 22, roof: "#D94F31", gable: true },
  storeB: { color: "#2FBF8F", w: 26, d: 26, h: 22, roof: "#1F9C72", gable: true },
  storeC: { color: "#9B87F5", w: 26, d: 26, h: 22, roof: "#7C66E0", gable: true },
};

const chf = (n: number) => `CHF ${n >= 1000 ? `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k` : n}`;
const subtitle: Record<SiteType, string> = {
  supplier: "Supplies parts upstream",
  plant: "Makes components",
  assembly: "Builds bikes",
  warehouse: "Ships to 3 stores",
  store: "Sells to customers",
};

// ---------- controls ----------

function inspectorFor(state: State, site: Site): InspectorModel {
  const look = LOOK[site.id];
  const icon = (
    <svg viewBox="-28 -46 56 56" width="40" height="40" aria-hidden>
      <Building x={0} y={0} {...look} w={look.w * 0.7} d={look.d * 0.7} h={look.h * 0.7} windows={false} chimney={false} />
    </svg>
  );
  const isWarehouse = site.type === "warehouse";
  return {
    title: site.name,
    level: site.level,
    subtitle: `${subtitle[site.type]} · selected`,
    icon,
    note: site.outOfStock ? "Out of stock — customers are leaving." : site.id === "tier2" ? "Storms nearby: deliveries may slip." : undefined,
    progress: isWarehouse
      ? { label: "Shipping cycle", value: "52 / day", pct: site.pct, tone: "amber" }
      : { label: site.type === "store" ? "Shelf fill" : "Utilisation", value: `${Math.round(site.pct * 100)}%`, pct: site.pct, tone: site.outOfStock ? "coral" : "amber" },
    stats: [
      { label: "Stock", value: String(site.stock), tone: site.stock === 0 ? "coral" : undefined },
      { label: "Incoming", value: `${site.incoming} · ${site.leadWeeks} wk` },
      { label: "Holding", value: `${chf(site.holdingPerWeek)}/wk`, tone: "coral" },
      { label: "Backlog", value: String(site.backlog), tone: site.backlog > 0 ? "coral" : undefined },
    ],
    primary: { id: "order", label: "Order", icon: "order", amount: isWarehouse ? 60 : 20, step: 10 },
    actions: [
      { id: "expand", label: `Expand · ${chf(isWarehouse ? 12000 : 8000)}`, sub: "+20% capacity, +8% holding cost", icon: "expand", variant: "soft" },
    ],
  };
}

export function toControls(state: State, selectedId: string | null): ControlsModel {
  const site = state.sites.find((s) => s.id === (selectedId ?? DEFAULT_SELECTED));
  return {
    brand: { world: state.world.name, seed: state.world.seed, difficulty: state.world.difficulty },
    topBar: {
      value: `CHF ${state.cash.toLocaleString("en-US")}`,
      chips: [{ text: `${state.perDay >= 0 ? "+" : ""}${state.perDay.toLocaleString("en-US")} / day`, tone: state.perDay >= 0 ? "mint" : "coral" }],
      timeLabel: `Week ${state.week} / ${state.weeks}`,
      timeProgress: state.week / state.weeks,
    },
    story: state.story,
    inspector: site && inspectorFor(state, site),
    discoveries: state.discoveries,
    goal: {
      text: "Grow to CHF 1M profit while serving ≥ 95% of customers",
      bars: [
        { label: "Profit", value: `${chf(state.goal.profit)} / 1M`, pct: state.goal.profit / state.goal.target, tone: "ink" },
        { label: "Customers served", value: `${Math.round(state.goal.served * 100)}% / ${Math.round(state.goal.servedTarget * 100)}%`, pct: state.goal.served, tone: "amber", tick: state.goal.servedTarget },
      ],
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
      verbs: [
        { id: "probe", label: "Probe", icon: "probe", key: "Q" },
        { id: "order", label: "Order", icon: "order", key: "W" },
        { id: "expand", label: "Expand", icon: "expand", key: "E" },
      ],
      active: state.dock.active,
      unlocked: state.dock.unlocked,
      total: state.dock.total,
    },
  };
}

// ---------- world view ----------

const VIEW_W = 880;
const VIEW_H = 640;
const grid = makeGrid({ cx: 440, cy: 318, n: N, size: 40 });

/** Manhattan path between two tiles: along i first, then along j (both ends included). */
function manhattan(a: Site, b: Site): [number, number][] {
  const out: [number, number][] = [[a.i, a.j]];
  let { i, j } = a;
  while (i !== b.i) { i += Math.sign(b.i - i); out.push([i, j]); }
  while (j !== b.j) { j += Math.sign(b.j - j); out.push([i, j]); }
  return out;
}

const key = (i: number, j: number) => `${i},${j}`;

export function WorldView({ state, selectedId, onSelect }: { state: State; selectedId: string | null; onSelect: (id: string) => void }) {
  const selected = selectedId ?? DEFAULT_SELECTED;
  const byId = new Map(state.sites.map((s) => [s.id, s]));
  const paths = state.routes.flatMap((r) => {
    const a = byId.get(r.from), b = byId.get(r.to);
    return a && b ? [{ r, tiles: manhattan(a, b) }] : [];
  });

  // Ground: which tiles are path or water.
  const kinds = new Map<string, TileKind>();
  for (const [i, j] of state.water) kinds.set(key(i, j), "water");
  const siteTiles = new Set(state.sites.map((s) => key(s.i, s.j)));
  for (const { tiles } of paths) for (const [i, j] of tiles) if (!siteTiles.has(key(i, j))) kinds.set(key(i, j), "path");

  // Objects in painter's order (i + j ascending = back to front).
  const items: { depth: number; node: ReactNode }[] = [];
  for (const [i, j, q] of state.fog) {
    const [x, y] = grid.at(i, j);
    items.push({ depth: i + j, node: <Fog key={`fog-${i}-${j}`} x={x} y={y} size={grid.size} question={q} /> });
  }
  state.trees.forEach(([i, j], k) => {
    const [x, y] = grid.at(i, j);
    items.push({ depth: i + j, node: <Tree key={`tree-${i}-${j}`} x={x} y={y} scale={0.85 + (k % 3) * 0.12} /> });
  });
  for (const [i, j] of state.workers) {
    const [x, y] = grid.at(i, j);
    items.push({ depth: i + j + 0.1, node: <Person key={`worker-${i}-${j}`} x={x - 6} y={y + 2} /> });
  }
  for (const s of state.sites) {
    const [x, y] = grid.at(s.i, s.j);
    items.push({
      depth: s.i + s.j + 0.2,
      node: (
        <g key={s.id} className="clickable" onClick={() => onSelect(s.id)}>
          <Building x={x} y={y} {...LOOK[s.id]} target={s.id} />
        </g>
      ),
    });
  }
  items.sort((a, b) => a.depth - b.depth);

  // Huds above each building, in percent of the view.
  const huds = state.sites.map((s) => {
    const [x, y] = grid.at(s.i, s.j);
    const top = y - buildingTop(LOOK[s.id]) - 34;
    const p = toPercent(x, top, VIEW_W, VIEW_H);
    return (
      <Hud
        key={s.id}
        x={p.x}
        y={p.y}
        level={s.level}
        label={s.outOfStock ? `${s.name} · out of stock` : s.name}
        pct={s.pct}
        color={LOOK[s.id].color}
        alert={s.outOfStock}
        selected={s.id === selected}
        onClick={() => onSelect(s.id)}
        target={s.id}
      />
    );
  });
  // Label above the fogged corner, kept inside the view.
  const [fx, fy] = grid.at(8, 0);
  const fogLabel = toPercent(Math.min(fx, VIEW_W - 110), fy - 70, VIEW_W, VIEW_H);
  const sel = byId.get(selected);

  return (
    <Stage
      width={VIEW_W}
      height={VIEW_H}
      overlay={
        <>
          {huds}
          <div className="world__label" style={{ left: `${fogLabel.x}%`, top: `${fogLabel.y}%` }}>
            <Chip tone="muted">UNEXPLORED · probe to reveal</Chip>
          </div>
        </>
      }
    >
      <IsoIsland grid={grid} tileKind={(i, j) => kinds.get(key(i, j)) ?? "grass"}>
        {/* Rings under the selected and the alerting sites. */}
        {sel && <polygon points={pts(grid.diamond(sel.i, sel.j, 1.45))} fill="none" stroke="var(--ink)" strokeWidth={2} strokeDasharray="6 4" />}
        {state.sites.filter((s) => s.outOfStock).map((s) => (
          <polygon key={`alert-${s.id}`} className="pulse" points={pts(grid.diamond(s.i, s.j, 1.4))} fill="rgba(255,107,74,0.12)" stroke="var(--coral)" strokeWidth={2.5} />
        ))}

        {/* Routes: dashed flows through the path tiles, one truck per leg. */}
        {paths.map(({ r, tiles }) => {
          const corner = tiles.findIndex(([i]) => i === tiles[tiles.length - 1][0]);
          const line: Pt[] = [tiles[0], tiles[corner], tiles[tiles.length - 1]].map(([i, j]) => grid.at(i, j));
          return <Flow key={`flow-${r.from}-${r.to}`} points={line} />;
        })}
        {paths.flatMap(({ r, tiles }) => {
          const corner = tiles.findIndex(([i]) => i === tiles[tiles.length - 1][0]);
          const legs: { from: Pt; to: Pt; dir: "u" | "v" }[] = [];
          if (corner > 0) legs.push({ from: grid.at(...tiles[0]), to: grid.at(...tiles[corner]), dir: "u" });
          if (corner < tiles.length - 1) legs.push({ from: grid.at(...tiles[corner]), to: grid.at(...tiles[tiles.length - 1]), dir: "v" });
          return legs.map((leg, k) => {
            const len = Math.hypot(leg.to[0] - leg.from[0], leg.to[1] - leg.from[1]);
            const dx = leg.to[0] - leg.from[0], dy = leg.to[1] - leg.from[1];
            const path = `M${leg.from[0]},${leg.from[1]} L${leg.to[0]},${leg.to[1]}`;
            // Driving "backwards" along an axis: mirror the truck so the cab leads.
            const back = leg.dir === "u" ? dx < 0 : dx > 0;
            return (
              <g key={`truck-${r.from}-${r.to}-${k}`} pointerEvents="none">
                <Vehicle x={0} y={0} dir={leg.dir} reverse={back} color={LOOK[r.from].color} scale={0.9} />
                <animateMotion dur={`${(len / 28).toFixed(1)}s`} repeatCount="indefinite" path={path} begin={`${(k * 0.7 + dy * 0.003).toFixed(2)}s`} />
              </g>
            );
          });
        })}

        {items.map((it) => it.node)}

        {/* Clouds over the fog, storm over Tier 2. */}
        <Cloud x={grid.at(9, 0)[0]} y={grid.at(9, 0)[1] - 28} scale={1.1} />
        <Cloud x={grid.at(0, 1)[0] + 10} y={grid.at(0, 1)[1] - 26} scale={0.9} />
        {state.storm && <Storm x={grid.at(...state.storm)[0] - 10} y={grid.at(...state.storm)[1] - 78} scale={0.9} />}
      </IsoIsland>
    </Stage>
  );
}
