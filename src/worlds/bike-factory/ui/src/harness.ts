// Connection to the agent harness (`harness serve`, proxied under /harness by Vite).
// Same in every world; do not edit per world. See decision 0007.
import { useEffect, useState } from "react";

/** The world server as the harness reaches it (set by vite.config.ts). */
declare const __WORLD_URL__: string;
const WORLD_URL = typeof __WORLD_URL__ === "string" ? __WORLD_URL__ : "http://127.0.0.1:8000";
const OFFLINE_RETRY_MS = 10000;

/** One agent from agents.toml. */
export interface AgentInfo { name: string; label: string; color?: string | null; model: string }

/** Who plays the world, from `state.play` (added by the base server). */
export interface Play { mode: "you" | "agent"; agent: string | null }

/** Outcome of the last agent run on this world. */
export interface LastRun { agent: string; stopped_by: string; error?: string; agent_steps?: number }

const FALLBACK_COLOR = "#7b61ff";

/** Display name and cursor colour of an agent (also for agents the harness does not list). */
export function agentLook(agents: AgentInfo[], name: string | null): { label: string; color: string } {
  const a = agents.find((x) => x.name === name);
  return { label: a?.label ?? name ?? "Agent", color: a?.color ?? FALLBACK_COLOR };
}

/** Agents the harness offers; `offline` while the harness is not running (retried). */
export function useAgents(): { agents: AgentInfo[]; offline: boolean } {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [offline, setOffline] = useState(false);
  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    const load = async () => {
      try {
        const res = await fetch("/harness/agents");
        if (!res.ok) throw new Error(String(res.status));
        const list = (await res.json()) as AgentInfo[];
        if (alive) { setAgents(list); setOffline(false); }
      } catch {
        if (alive) { setOffline(true); timer = setTimeout(load, OFFLINE_RETRY_MS); }
      }
    };
    void load();
    return () => { alive = false; clearTimeout(timer); };
  }, []);
  return { agents, offline };
}

async function post(path: string, body: unknown): Promise<{ ok: boolean; error?: string }> {
  try {
    const res = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (res.ok) return { ok: true };
    const detail = await res.json().then((d: { detail?: unknown }) => d.detail).catch(() => null);
    return { ok: false, error: typeof detail === "string" ? detail : `Harness: HTTP ${res.status}` };
  } catch {
    return { ok: false, error: "No connection to the harness (pixi run harness serve)" };
  }
}

/** Let `agent` play from the current week (no reset, fresh budget). */
export function startAgent(agent: string) {
  return post("/harness/run", { world_url: WORLD_URL, agent });
}

/** Stop the agent and take over by hand. Without a harness, unlock the world directly. */
export async function stopAgent() {
  const sent = await post("/harness/stop", { world_url: WORLD_URL });
  if (sent.ok) return sent;
  return post("/api/action", { id: "mode", args: { mode: "you" } });
}

/** Seconds the agent waits before each tool call; changes a running agent at once. */
export function setPace(seconds: number) {
  return post("/harness/pace", { world_url: WORLD_URL, seconds });
}

/** Current pace for this world, or null without a harness. */
export async function getPace(): Promise<number | null> {
  try {
    const res = await fetch(`/harness/status?world_url=${encodeURIComponent(WORLD_URL)}`);
    return res.ok ? ((await res.json()) as { pace: number }).pace : null;
  } catch {
    return null;
  }
}

/** How the last agent run on this world ended, or null. */
export async function lastRun(): Promise<LastRun | null> {
  try {
    const res = await fetch(`/harness/status?world_url=${encodeURIComponent(WORLD_URL)}`);
    return res.ok ? ((await res.json()) as { last: LastRun | null }).last : null;
  } catch {
    return null;
  }
}
