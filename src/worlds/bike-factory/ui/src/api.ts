// Connection to the world server (server/api.py, proxied under /api by Vite).
import { useCallback, useEffect, useRef, useState } from "react";

const POLL_MS = 1000;
const OFFLINE_POLL_MS = 5000;

/**
 * Current world state and a `refresh()` to fetch it right away (e.g. after an
 * action). Polls `GET /api/state` every second; until the server answers (or
 * while it is down) the last known state, initially `mock`, is kept, so the UI
 * also works without a server. Unchanged responses keep the same object, so
 * nothing re-renders.
 */
export function useWorldState<T>(mock: T): [T, () => Promise<void>] {
  const [state, setState] = useState<T>(mock);
  const last = useRef("");
  const fetchState = useCallback(async (): Promise<boolean> => {
    try {
      const res = await fetch("/api/state");
      if (!res.ok) return false;
      const text = await res.text();
      if (text !== last.current) {
        last.current = text;
        setState(JSON.parse(text) as T);
      }
      return true;
    } catch {
      return false; // No server: keep the current (mock) state.
    }
  }, []);

  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      const ok = await fetchState();
      // Back off while the server is unreachable to keep the console quiet.
      if (alive) timer = setTimeout(poll, ok ? POLL_MS : OFFLINE_POLL_MS);
    };
    void poll();
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [fetchState]);

  const refresh = useCallback(async () => {
    await fetchState();
  }, [fetchState]);
  return [state, refresh];
}

/** Outcome of a request: `error` is the server's reason when it was rejected. */
export interface Sent { ok: boolean; error?: string }

async function post(path: string, body: unknown): Promise<Sent> {
  try {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (res.ok) return { ok: true };
    const detail = await res.json().then((d: { detail?: unknown }) => d.detail).catch(() => null);
    return { ok: false, error: typeof detail === "string" ? detail : `HTTP ${res.status}` };
  } catch {
    return { ok: false, error: "No connection to the world server" };
  }
}

/** Send a player action (queued until the next advance) or a UI control. */
export function sendAction(id: string, args: Record<string, unknown> = {}): Promise<Sent> {
  return post("/api/action", { id, args });
}

/** Remove queued action `index` of this step. */
export function unqueue(index: number): Promise<Sent> {
  return post("/api/unqueue", { index });
}
