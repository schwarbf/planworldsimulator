import { type FormEvent, useState } from "react";

import { Link } from "react-router";

import { api, ApiError, type World } from "../api/client";
import { SHOWCASE } from "../data/showcase";
import { cx } from "./ui";

export interface Draft {
  name: string;
  prompt: string;
}

interface Props {
  draft: Draft;
  onDraftChange: (draft: Draft) => void;
  onCreated: (world: World) => void;
}

const GRID = "var(--color-line)";

export function PromptWindow({ draft, onDraftChange, onCreated }: Props) {
  const { name, prompt } = draft;
  const [seed, setSeed] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [existing, setExisting] = useState<string | null>(null);

  const canSubmit =
    name.trim().length >= 2 && prompt.trim().length >= 3 && !busy;
  const activeTheme = SHOWCASE.find((w) => w.prompt === prompt)?.name;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setExisting(null);
    try {
      const world = await api.createWorld({
        name: name.trim(),
        prompt: prompt.trim(),
        seed: seed === "" ? undefined : Number(seed),
      });
      onCreated(world);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      if (err instanceof ApiError) setExisting(err.existingWorld);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      aria-labelledby="hero-title"
      className="flex min-h-[min(calc(100svh-4rem),64rem)] flex-col px-5 pt-10 pb-8 sm:px-8 sm:pt-14 lg:px-12"
      style={{
        backgroundImage: `linear-gradient(${GRID} 1px, transparent 1px), linear-gradient(90deg, ${GRID} 1px, transparent 1px)`,
        backgroundSize: "40px 40px",
        backgroundPosition: "-1px -1px",
      }}
    >
      <p className="font-mono text-xs tracking-wide text-muted uppercase">
        01 · Describe
      </p>
      <h1
        id="hero-title"
        className="mt-3 max-w-5xl font-display text-[clamp(2.75rem,7vw,6.5rem)] leading-[0.95] tracking-tight"
      >
        Describe a planning world,
        <br />
        <em className="text-coral">get a benchmark.</em>
      </h1>
      <p className="mt-5 max-w-2xl text-lg text-muted">
        Write what the world is about in plain language. PlanWorldSimulator
        generates the simulator, the agent interface and a playable website,
        with three difficulty levels built in.
      </p>

      <form
        onSubmit={submit}
        className="mt-8 flex min-h-80 flex-1 flex-col overflow-hidden rounded-xl border border-ink bg-card shadow-card"
      >
        <label className="flex items-baseline gap-4 border-b border-line px-5 pt-5 pb-3 sm:px-7">
          <span className="font-mono text-xs text-muted uppercase">Name</span>
          <input
            aria-label="World name"
            value={name}
            maxLength={60}
            onChange={(e) => onDraftChange({ ...draft, name: e.target.value })}
            placeholder="e.g. Fission Ops"
            className="min-w-0 flex-1 bg-transparent font-display text-3xl outline-none placeholder:text-muted/60 sm:text-4xl"
          />
        </label>
        <textarea
          aria-label="Describe your benchmark"
          value={prompt}
          onChange={(e) => onDraftChange({ ...draft, prompt: e.target.value })}
          placeholder="A bakery chain that must plan flour orders while a hidden supplier strike looms…"
          className="min-h-48 flex-1 resize-none bg-transparent p-5 text-xl leading-relaxed outline-none placeholder:text-muted/70 sm:p-7 sm:text-2xl"
        />
        <div className="flex flex-col gap-4 border-t border-line bg-sand-2 px-5 py-4 sm:px-7 lg:flex-row lg:items-center">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
            <span className="font-mono text-xs text-muted uppercase">
              Start from
            </span>
            {SHOWCASE.map((world) => (
              <button
                key={world.name}
                type="button"
                onClick={() =>
                  onDraftChange({ name: world.name, prompt: world.prompt })
                }
                className={cx(
                  "underline-offset-4 hover:underline",
                  world.name === activeTheme && "font-semibold underline",
                )}
              >
                {world.name}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-3 lg:ml-auto">
            <label className="flex items-center gap-2 font-mono text-xs text-muted">
              SEED
              <input
                aria-label="Seed"
                inputMode="numeric"
                value={seed}
                onChange={(e) => setSeed(e.target.value.replace(/\D/g, ""))}
                placeholder="random"
                className="w-20 rounded-md border border-line bg-card px-2 py-1.5 text-ink outline-none focus:border-ink"
              />
            </label>
            <button
              type="submit"
              disabled={!canSubmit}
              className="rounded-md bg-coral px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-coral-dark disabled:cursor-not-allowed disabled:opacity-50"
            >
              {busy ? "Starting…" : "Generate world"}
            </button>
          </div>
        </div>
      </form>
      {error && (
        <p role="alert" className="mt-3 text-sm text-bad">
          {error}
          {existing && (
            <>
              {" "}
              <Link
                to={`/worlds/${existing}`}
                className="font-semibold underline"
              >
                Open it
              </Link>
            </>
          )}
        </p>
      )}
    </section>
  );
}
