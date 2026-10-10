// Default template contract; replaced from design.json during generation.
export interface State {
  world: { name: string; seed: string; difficulty: string };
  week: number;
  weeks: number;
  cash: number;
  capacity: number;
  demand: number;
  profit: number;
  target: number;
  story?: { tag: string; text: string; tone: "amber" | "mint" | "coral" } | null;
  discoveries: { total: number; found: string[]; hidden: (string | null)[] };
  agent: { experiment: number; experiments: number; mode: "you" | "agent"; scores: number[]; baseline: number; now: string; code: string };
  active?: string | null;
  done?: boolean;
}

export const mockState: State = {
  world: { name: "Example world", seed: "1234", difficulty: "Medium" },
  week: 1,
  weeks: 12,
  cash: 1000,
  capacity: 10,
  demand: 30,
  profit: 0,
  target: 3500,
  story: { tag: "WEEK 1", text: "Replace this placeholder world with your own.", tone: "mint" },
  discoveries: { total: 0, found: [], hidden: [] },
  agent: { experiment: 1, experiments: 20, mode: "you", scores: [0], baseline: 0.5, now: "Waiting for a hypothesis…", code: "# no agent calls yet" },
};

