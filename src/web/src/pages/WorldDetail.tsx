import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { Link, useParams } from "react-router";

import { api, type World, type WorldEvent } from "../api/client";
import { PlayLevels } from "../components/PlayLevels";
import { Button, Card, cx, Label, StatusChip } from "../components/ui";

const STEPS = [
  { key: "check_exists", label: "Name" },
  { key: "copy_template", label: "Preparation" },
  { key: "design", label: "Design" },
  { key: "sim", label: "Simulator" },
  { key: "ui", label: "World view" },
  { key: "tests", label: "Validation" },
  { key: "polish", label: "Look" },
  { key: "smoke", label: "Build and boot" },
  { key: "publish", label: "Publication" },
];

type StepState = "pending" | "active" | "done" | "failed";

function stepState(key: string, events: WorldEvent[], world: World): StepState {
  const last = events.filter((e) => e.step === key).at(-1);
  // A published world is complete, even if a later step reopened an earlier one.
  if (last && world.status === "ready") return "done";
  if (last?.state === "done") return "done";
  if (last?.state === "failed" || last?.state === "exists") return "failed";
  if (last) return world.status === "failed" ? "failed" : "active";
  return "pending";
}

/** Icons of the live-log lines (event `kind`). */
const TRACE_ICON: Record<string, string> = {
  write: "✎",
  edit: "✎",
  read: "◱",
  run: "▶",
  text: "“",
  ok: "✓",
  bad: "✗",
};
const TRACE_TONE: Record<string, string> = {
  text: "italic text-white/70",
  ok: "text-good",
  bad: "text-[#ff9f8a]",
};

function clock(seconds: number): string {
  const s = Math.floor(seconds);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

/** The full live log of one step, shown on hover; follows the newest line. */
function TracePanel({
  label,
  lines,
  live,
}: {
  label: string;
  lines: WorldEvent[];
  live: boolean;
}) {
  const box = useRef<HTMLDivElement | null>(null);
  useLayoutEffect(() => {
    if (box.current) box.current.scrollTop = box.current.scrollHeight;
  }, [lines.length]);
  return (
    <div
      ref={box}
      role="log"
      aria-label={`${label} trace`}
      className="invisible absolute top-full right-0 left-5 z-10 mt-1 max-h-72 overflow-y-auto rounded-xl bg-ink px-4 py-3 text-white opacity-0 shadow-[0_16px_40px_rgba(27,31,59,0.25)] transition-opacity group-hover:visible group-hover:opacity-100"
    >
      <div className="mb-2 flex justify-between font-mono text-[11px] tracking-wide text-white/50 uppercase">
        <span>
          {label} · {live ? "live trace" : "trace"}
        </span>
        <span>{lines.length} events</span>
      </div>
      {lines.map((line) => (
        <div
          key={line.id}
          className={cx(
            "grid grid-cols-[2.75rem_1rem_1fr] gap-2 py-0.5 text-xs leading-snug",
            TRACE_TONE[line.kind ?? ""],
          )}
        >
          <span className="font-mono text-[11px] text-white/40 tabular-nums">
            {clock(line.elapsed_seconds)}
          </span>
          <span aria-hidden>{TRACE_ICON[line.kind ?? ""] ?? "·"}</span>
          <span className="break-words">{line.message}</span>
        </div>
      ))}
    </div>
  );
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
  const [eventLog, setEventLog] = useState<{
    id: string;
    attempt: number;
    events: WorldEvent[];
  }>({ id: "", attempt: 0, events: [] });
  const [missing, setMissing] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const [connected, setConnected] = useState(true);
  const [now, setNow] = useState(() => Date.now());
  const attempt = world?.generation_attempt ?? 1;
  const allEvents =
    eventLog.id === id && eventLog.attempt === attempt ? eventLog.events : [];
  // Live-log lines ("trace") are shown under their step; the rest drives the steps.
  const events = allEvents.filter((e) => e.state !== "trace");
  const traces = allEvents.filter((e) => e.state === "trace");

  const reload = useCallback(async () => {
    try {
      setWorld(await api.getWorld(id));
    } catch {
      setMissing(true);
    }
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    void api
      .getWorld(id)
      .then((value) => {
        if (!cancelled) {
          setWorld(value);
          setMissing(false);
        }
      })
      .catch(() => {
        if (!cancelled) setMissing(true);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  const loaded = world?.id === id;
  useEffect(() => {
    if (!loaded) return;
    let cancelled = false;
    const source = new EventSource(
      `/api/worlds/${id}/stream?attempt=${attempt}`,
    );
    function merge(incoming: WorldEvent[]) {
      if (cancelled) return;
      setEventLog((log) => {
        const current =
          log.id === id && log.attempt === attempt ? log.events : [];
        const byId = new Map(current.map((event) => [event.id, event]));
        for (const event of incoming) {
          if (event.attempt === attempt) byId.set(event.id, event);
        }
        return {
          id,
          attempt,
          events: [...byId.values()].sort((a, b) => a.id - b.id),
        };
      });
    }
    // Restore history even when the stream reconnects from Last-Event-ID.
    void api
      .listEvents(id, attempt)
      .then((history) => {
        if (!cancelled) merge(history);
      })
      .catch(() => {});
    source.onopen = () => setConnected(true);
    source.onerror = () => setConnected(false);
    source.addEventListener("step", (message) => {
      const event = JSON.parse((message as MessageEvent).data) as WorldEvent;
      merge([event]);
      if (
        (event.step === "design" && event.state === "done") ||
        (event.step === "check_exists" && event.state === "started")
      )
        void reload();
    });
    source.addEventListener("done", () => {
      source.close();
      setConnected(true);
      void reload();
    });
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => {
      cancelled = true;
      source.close();
      clearInterval(timer);
    };
  }, [id, attempt, loaded, reload]);

  async function retry() {
    setRetrying(true);
    setActionError(null);
    try {
      const next = await api.retryWorld(id);
      setWorld(next);
    } catch (error) {
      setActionError(
        error instanceof Error
          ? error.message
          : "Could not retry. Try again shortly.",
      );
    } finally {
      setRetrying(false);
    }
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
              {world.generation_model && ` · ${world.generation_model}`}
            </p>
          </div>
          <StatusChip status={world.status} />
        </div>
        <p className="text-sm text-muted">{world.prompt}</p>
      </Card>

      <Card className="flex flex-col gap-4 p-6">
        <Label>Generation · Attempt {attempt}</Label>
        <p className="text-xs text-muted" aria-live="polite">
          {(() => {
            const last = allEvents.at(-1);
            if (!last)
              return world.status === "queued"
                ? "Waiting to start…"
                : "Loading progress…";
            const live =
              world.status === "generating"
                ? Math.max(0, (now - Date.parse(last.created_at)) / 1000)
                : 0;
            return `${Math.floor(last.elapsed_seconds + live)}s elapsed`;
          })()}
          {!connected && " · Reconnecting to progress…"}
        </p>
        <ol className="flex flex-col gap-3">
          {STEPS.map((step) => {
            const state = stepState(step.key, events, world);
            const last = [...events].reverse().find((e) => e.step === step.key);
            const lines = traces.filter((e) => e.step === step.key);
            const newest = lines.at(-1);
            const live = state === "active" && newest !== undefined;
            return (
              <li
                key={step.key}
                className="group relative flex flex-col gap-1.5"
              >
                <div className="flex items-center gap-3">
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
                  {!live && lines.length > 0 && (
                    <span className="font-mono text-[11px] text-muted/80">
                      {lines.length} ▾
                    </span>
                  )}
                </div>
                {live && (
                  <div className="ml-5 flex w-fit max-w-[calc(100%-1.25rem)] items-center gap-2 rounded-lg bg-sand px-2.5 py-1 text-xs">
                    <span aria-hidden>
                      {TRACE_ICON[newest.kind ?? ""] ?? "·"}
                    </span>
                    <span
                      key={newest.id}
                      className="animate-[fade-in_.35s_ease-out] truncate"
                      aria-live="polite"
                    >
                      {newest.message}
                    </span>
                    <span className="shrink-0 font-mono text-[11px] text-muted">
                      {lines.length} ▾
                    </span>
                  </div>
                )}
                {lines.length > 0 && (
                  <TracePanel label={step.label} lines={lines} live={live} />
                )}
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
              <Button
                variant="dark"
                disabled={retrying}
                onClick={() => void retry()}
              >
                {retrying ? "Retrying…" : "Retry"}
              </Button>
            )}
          </div>
        )}
      </Card>

      {actionError && (
        <p role="alert" className="text-sm text-bad">
          {actionError}
        </p>
      )}

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
