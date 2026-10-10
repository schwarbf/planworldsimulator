import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router";

import { api, type World } from "../api/client";
import { Button, Card, StatusChip } from "./ui";

const POLL_MS = 2000;

export function WorldsList() {
  const [worlds, setWorlds] = useState<World[] | null>(null);

  const refresh = useCallback(async () => {
    try {
      setWorlds(await api.listWorlds());
    } catch {
      setWorlds((current) => current ?? []);
    }
  }, []);

  useEffect(() => {
    const first = setTimeout(refresh, 0);
    const timer = setInterval(refresh, POLL_MS);
    return () => {
      clearTimeout(first);
      clearInterval(timer);
    };
  }, [refresh]);

  async function toggle(world: World) {
    await (world.running ? api.stopWorld(world.id) : api.startWorld(world.id));
    await refresh();
  }

  return (
    <section>
      <h2 className="mb-4 font-display text-xl font-bold">Your worlds</h2>
      {worlds === null ? (
        <p className="text-sm text-muted">Loading…</p>
      ) : worlds.length === 0 ? (
        <Card className="p-6 text-sm text-muted">
          No worlds yet. Describe one above and hit Generate.
        </Card>
      ) : (
        <Card className="divide-y divide-line">
          {worlds.map((world) => (
            <div
              key={world.id}
              className="flex flex-wrap items-center gap-3 px-5 py-4"
            >
              <div className="min-w-0 flex-1">
                <Link
                  to={`/worlds/${world.id}`}
                  className="block truncate font-semibold hover:underline"
                >
                  {world.title}
                </Link>
                <p className="text-xs text-muted">
                  Seed #{world.seed} · L{world.difficulty}
                  {world.running && world.port
                    ? ` · running on :${world.port}`
                    : ""}
                </p>
              </div>
              <StatusChip status={world.status} />
              <Link
                to={`/worlds/${world.id}`}
                className="rounded-xl bg-sand px-3 py-2 text-xs font-semibold hover:bg-line"
              >
                Open
              </Link>
              {world.status === "ready" && (
                <Button
                  variant={world.running ? "soft" : "dark"}
                  className="px-3 py-2 text-xs"
                  onClick={() => toggle(world)}
                >
                  {world.running ? "Stop" : "Start"}
                </Button>
              )}
            </div>
          ))}
        </Card>
      )}
    </section>
  );
}
