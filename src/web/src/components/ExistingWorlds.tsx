import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router";

import { api, type World } from "../api/client";
import { Section } from "./Section";
import { StatusChip } from "./ui";

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
    <Section
      id="worlds"
      index="05"
      label="Your worlds"
      title={<>What you have generated.</>}
    >
      {worlds === null ? (
        <p className="text-sm text-muted">Loading…</p>
      ) : worlds.length === 0 ? (
        <p className="rounded-lg border border-dashed border-line p-8 text-sm text-muted">
          No worlds yet. Describe one at the top of the page and hit Generate.
        </p>
      ) : (
        <ul className="border-t border-ink">
          {worlds.map((world) => (
            <li
              key={world.id}
              className="flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-line py-4"
            >
              <div className="min-w-0 flex-1 basis-64">
                <Link
                  to={`/worlds/${world.id}`}
                  className="block truncate font-display text-2xl hover:underline"
                >
                  {world.title}
                </Link>
                <p className="font-mono text-xs text-muted">
                  seed #{world.seed} · {world.levels.length} levels
                  {world.running && world.port
                    ? ` · running on :${world.port}`
                    : ""}
                </p>
              </div>
              <StatusChip status={world.status} />
              <Link
                to={`/worlds/${world.id}`}
                className="text-sm font-semibold underline-offset-4 hover:underline"
              >
                Open
              </Link>
              {world.status === "ready" && (
                <button
                  type="button"
                  onClick={() => toggle(world)}
                  className="rounded-md border border-ink px-3 py-1.5 text-sm font-semibold hover:bg-ink hover:text-white"
                >
                  {world.running ? "Stop" : "Start"}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}
