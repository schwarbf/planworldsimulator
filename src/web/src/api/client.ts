export type WorldStatus = "queued" | "generating" | "ready" | "failed";

export interface World {
  id: string;
  title: string;
  prompt: string;
  seed: number;
  levels: number[];
  status: WorldStatus;
  storyline: string | null;
  path: string | null;
  running: boolean;
  port: number | null;
  featured: boolean;
  play_count: number;
  /** True when this browser created the world. */
  mine: boolean;
  created_at: string;
  updated_at: string;
}

export interface WorldPage {
  items: World[];
  total: number;
}

export interface WorldEvent {
  id: number;
  step: string;
  state: "started" | "done" | "failed";
  message: string;
  created_at: string;
}

export interface CreateWorld {
  name: string;
  prompt: string;
  seed?: number;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${await response.text()}`);
  }
  return (await response.json()) as T;
}

export const api = {
  listWorlds: ({ q = "", limit = 12 }: { q?: string; limit?: number } = {}) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (q) params.set("q", q);
    return request<WorldPage>(`/worlds?${params}`);
  },
  getWorld: (id: string) => request<World>(`/worlds/${id}`),
  listEvents: (id: string) => request<WorldEvent[]>(`/worlds/${id}/events`),
  createWorld: (body: CreateWorld) =>
    request<World>("/worlds", { method: "POST", body: JSON.stringify(body) }),
  retryWorld: (id: string) =>
    request<World>(`/worlds/${id}/retry`, { method: "POST" }),
};

/** Display names of the difficulty levels, indexed by level - 1. */
export const LEVEL_NAMES = ["Easy", "Medium", "Hard"];

/** Public link that starts the world on demand and opens it at a level. */
export function playUrl(worldId: string, level: number): string {
  return `/api/play/${worldId}/?level=${level}`;
}
