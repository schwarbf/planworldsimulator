import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router";

import { api, type World, type WorldEvent } from "../api/client";
import { PlayLevels } from "../components/PlayLevels";
import { Button, Card, cx, Label, StatusChip } from "../components/ui";

const STEPS = [
  { key: "check_exists", label: "Check the name" },
  { key: "copy_template", label: "Copy template" },
  { key: "design", label: "Design" },
  { key: "fill", label: "Write simulator and world view" },
  { key: "tests", label: "Tests" },
  { key: "smoke", label: "Build and boot" },
  { key: "publish", label: "Publish" },
];

type StepState = "pending" | "active" | "done" | "failed";

function stepState(key: string, events: WorldEvent[], world: World): StepState {
  const mine = events.filter((e) => e.step === key);
  if (mine.some((e) => e.state === "done")) return "done";
  if (mine.some((e) => e.state === "exists")) return "failed";
  if (mine.length > 0) {
    return world.status === "failed" || mine.some((e) => e.state === "failed")
      ? "failed"
      : "active";
  }
  return "pending";
}

const DOT: Record<StepState, string> = {
  pending: "bg-line",
  active: "animate-pulse bg-violet",
  done: "bg-good",
  failed: "bg-bad",
};

export function WorldDetail() {
  const { id = "" } = useParams();
  const [world, setWorld] = useState<World | null>(null);
  const [events, setEvents] = useState<WorldEvent[]>([]);
  const [missing, setMissing] = useState(false);

  const reload = useCallback(async () => {
    try {
      setWorld(await api.getWorld(id));
    } catch {
      setMissing(true);
    }
  }, [id]);

  useEffect(() => {
    const first = setTimeout(reload, 0);
    const source = new EventSource(`/api/worlds/${id}/stream`);
    source.addEventListener("step", (message) => {
      const event = JSON.parse((message as MessageEvent).data) as WorldEvent;
      setEvents((current) =>
        current.some((e) => e.id === event.id) ? current : [...current, event],
      );
      void reload();
    });
    source.addEventListener("done", () => {
      source.close();
      void reload();
    });
    return () => {
      clearTimeout(first);
      source.close();
    };
  }, [id, reload]);

  async function act(action: (id: string) => Promise<World>) {
    setWorld(await action(id));
  }

  if (missing) {
    return (
      <main className="mx-auto max-w-3xl px-5 pb-20">
        <p className="text-sm text-muted">World not found.</p>
        <Link to="/" className="text-sm font-semibold underline">
          Back to start
        </Link>
      </main>
    );
  }
  if (!world) {
    return (
      <main className="mx-auto max-w-3xl px-5 text-sm text-muted">
        Loading…
      </main>
    );
  }

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-5 px-5 pt-10 pb-20">
      <Link to="/" className="text-sm text-muted hover:underline">
        ← All worlds
      </Link>
      <Card className="flex flex-col gap-4 p-6">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="font-display text-4xl">{world.title}</h1>
            <p className="text-xs text-muted">
              World {world.id} · Seed #{world.seed} · {world.levels.length}{" "}
              difficulty levels
            </p>
          </div>
          <StatusChip status={world.status} />
        </div>
        <p className="text-sm text-muted">{world.prompt}</p>
      </Card>

      <Card className="flex flex-col gap-4 p-6">
        <Label>Generation</Label>
        <ol className="flex flex-col gap-3">
          {STEPS.map((step) => {
            const state = stepState(step.key, events, world);
            const last = [...events].reverse().find((e) => e.step === step.key);
            return (
              <li key={step.key} className="flex items-center gap-3">
                <span className={cx("size-2.5 rounded-full", DOT[state])} />
                <span
                  className={cx(
                    "text-sm font-semibold",
                    state === "pending" && "text-muted",
                  )}
                >
                  {step.label}
                </span>
                <span className="text-xs text-muted">{last?.message}</span>
              </li>
            );
          })}
        </ol>
        {world.status === "exists" && (
          <p role="alert" className="text-sm text-bad">
            A world called “{world.title}” already exists.{" "}
            {world.duplicate_of && (
              <Link
                to={`/worlds/${world.duplicate_of}`}
                className="font-semibold underline"
              >
                Open it
              </Link>
            )}
          </p>
        )}
        {world.status === "failed" && (
          <div className="flex items-center gap-3">
            <p role="alert" className="text-sm text-bad">
              {[...events].reverse().find((e) => e.state === "failed")
                ?.message ?? "Generation failed"}
            </p>
            {world.mine && (
              <Button variant="dark" onClick={() => act(api.retryWorld)}>
                Retry
              </Button>
            )}
          </div>
        )}
      </Card>

      {world.storyline && (
        <Card className="flex flex-col gap-2 p-6">
          <Label>Storyline</Label>
          <p className="text-sm">{world.storyline}</p>
        </Card>
      )}

      {world.status === "ready" && (
        <Card className="flex flex-col gap-3 p-6">
          <div>
            <p className="font-semibold">Play this world</p>
            <p className="text-xs text-muted">
              Public: anyone with the link can play. It starts when someone
              opens it and stops after a while without players.
              {world.play_count > 0 && ` Played ${world.play_count}×.`}
            </p>
          </div>
          <PlayLevels world={world} />
        </Card>
      )}
    </main>
  );
}
