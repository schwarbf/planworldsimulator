// Connection to the world server (server/api.py, proxied under /api by Vite).
import { useEffect, useState } from "react";

const POLL_MS = 1000;
const OFFLINE_POLL_MS = 5000;

/**
 * Current world state. Polls `GET /api/state` every second; until the server
 * answers (or while it is down) the last known state, initially `mock`, is kept,
 * so the UI also works without a server.
 */
export function useWorldState<T>(mock: T): T {
  const [state, setState] = useState<T>(mock);
  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      let ok = false;
      try {
        const res = await fetch("/api/state");
        if (res.ok) {
          const next = (await res.json()) as T;
          if (alive) setState(next);
          ok = true;
        }
      } catch {
        // No server: keep the current (mock) state.
      }
      // Back off while the server is unreachable to keep the console quiet.
      if (alive) timer = setTimeout(poll, ok ? POLL_MS : OFFLINE_POLL_MS);
    };
    void poll();
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, []);
  return state;
}

/** Send a player action to the server; network errors are only logged. */
export async function sendAction(id: string, args: Record<string, unknown> = {}): Promise<void> {
  try {
    const res = await fetch("/api/action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, args }),
    });
    if (!res.ok) console.info(`action ${id} rejected: HTTP ${res.status}`);
  } catch (err) {
    console.info(`action ${id} not sent (no server)`, err);
  }
}
