export type WorldStatus =
  "queued" | "generating" | "ready" | "failed" | "exists";

export interface World {
  id: string;
  title: string;
  prompt: string;
  seed: number;
  levels: number[];
  status: WorldStatus;
  generation_attempt?: number;
  /** Generator model id (see `api.listModels`); null for older worlds. */
  generation_model?: string | null;
  storyline: string | null;
  path: string | null;
  /** With status "exists": the world that already has this name. */
  duplicate_of: string | null;
  running: boolean;
  port: number | null;
  featured: boolean;
  play_count: number;
  /** True when this browser created the world. */
  mine: boolean;
  has_thumbnail: boolean;
  created_at: string;
  updated_at: string;
}

export interface WorldPage {
  items: World[];
  total: number;
}

export interface WorldEvent {
  id: number;
  attempt: number;
  elapsed_seconds: number;
  step: string;
  /** "trace": one line of the generator's live log for `step`. */
  state: "started" | "done" | "failed" | "exists" | "trace";
  message: string;
  /** Live-log lines only: write, edit, read, run, text, ok, bad. */
  kind?: string | null;
  created_at: string;
}

export interface CreateWorld {
  name: string;
  prompt: string;
  seed?: number;
  model?: string;
}

/** A model the world generator can use. */
export interface GeneratorModel {
  id: string;
  label: string;
  note: string;
  default: boolean;
}

/** An error answer from the API: `detail` is the readable message. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
    /** Set when the name is taken: the world that has it. */
    readonly existingWorld: string | null = null,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const text = await response.text();
    let detail = text;
    try {
      const body = JSON.parse(text) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // not JSON: keep the text
    }
    throw new ApiError(
      response.status,
      detail,
      response.headers.get("X-Existing-World"),
    );
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
  listModels: () => request<GeneratorModel[]>("/worlds/models"),
  listEvents: (id: string, attempt?: number) =>
    request<WorldEvent[]>(
      `/worlds/${id}/events${attempt ? `?attempt=${attempt}` : ""}`,
    ),
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
