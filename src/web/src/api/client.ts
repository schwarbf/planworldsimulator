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
  created_at: string;
  updated_at: string;
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
  listWorlds: () => request<World[]>("/worlds"),
  getWorld: (id: string) => request<World>(`/worlds/${id}`),
  listEvents: (id: string) => request<WorldEvent[]>(`/worlds/${id}/events`),
  createWorld: (body: CreateWorld) =>
    request<World>("/worlds", { method: "POST", body: JSON.stringify(body) }),
  retryWorld: (id: string) =>
    request<World>(`/worlds/${id}/retry`, { method: "POST" }),
  startWorld: (id: string) =>
    request<World>(`/worlds/${id}/start`, { method: "POST" }),
  stopWorld: (id: string) =>
    request<World>(`/worlds/${id}/stop`, { method: "POST" }),
};
