import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router";

import { api, type World, type WorldEvent } from "../api/client";
import { Button, Card, cx, Label, StatusChip } from "../components/ui";

const STEPS = [
  { key: "storyline", label: "Storyline" },
  { key: "copy_template", label: "Copy template" },
  { key: "fill_template", label: "Fill template" },
  { key: "tests", label: "Tests" },
];

type StepState = "pending" | "active" | "done" | "failed";

function stepState(key: string, events: WorldEvent[], world: World): StepState {
  const mine = events.filter((e) => e.step === key);
  if (mine.some((e) => e.state === "done")) return "done";
  if (mine.length > 0) return world.status === "failed" ? "failed" : "active";
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
        {world.status === "failed" && (
          <div className="flex items-center gap-3">
            <p role="alert" className="text-sm text-bad">
              {events.find((e) => e.state === "failed")?.message ??
                "Generation failed"}
            </p>
            <Button variant="dark" onClick={() => act(api.retryWorld)}>
              Retry
            </Button>
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
        <Card className="flex items-center justify-between gap-3 p-6">
          <div>
            <p className="font-semibold">
              {world.running ? "World is running" : "World is ready"}
            </p>
            <p className="text-xs text-muted">
              {world.running && world.port
                ? `Serving on port ${world.port}`
                : "Start it to play or hand it to an agent."}
            </p>
          </div>
          <Button
            variant={world.running ? "soft" : "primary"}
            onClick={() => act(world.running ? api.stopWorld : api.startWorld)}
          >
            {world.running ? "Stop" : "Start world"}
          </Button>
        </Card>
      )}
    </main>
  );
}
