import { type FormEvent, useState } from "react";

import { api, type World } from "../api/client";
import { promptForTheme, THEMES } from "../data/showcase";
import { DifficultyPicker } from "./DifficultyPicker";
import { Button, Card, Chip, Label } from "./ui";

interface Props {
  prompt: string;
  onPromptChange: (prompt: string) => void;
  onCreated: (world: World) => void;
}

export function GeneratorCard({ prompt, onPromptChange, onCreated }: Props) {
  const [difficulty, setDifficulty] = useState(2);
  const [seed, setSeed] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeTheme = THEMES.find((t) => promptForTheme(t) === prompt);
  const canSubmit = prompt.trim().length >= 3 && !busy;

  function surprise() {
    const pick = THEMES[Math.floor(Math.random() * THEMES.length)];
    onPromptChange(promptForTheme(pick));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const world = await api.createWorld({
        prompt: prompt.trim(),
        difficulty,
        seed: seed === "" ? undefined : Number(seed),
      });
      onCreated(world);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="p-6">
      <form onSubmit={submit} className="flex flex-col gap-4">
        <div>
          <h2 className="font-display text-[22px] font-bold">New world</h2>
          <p className="text-xs text-muted">
            Every world is generated on demand — new network, delays, hidden
            rules and story.
          </p>
        </div>

        <Label>Describe your benchmark</Label>
        <textarea
          aria-label="Describe your benchmark"
          value={prompt}
          onChange={(e) => onPromptChange(e.target.value)}
          rows={4}
          placeholder="A bakery chain that must plan flour orders while a hidden supplier strike looms…"
          className="resize-none rounded-xl border border-line bg-sand-2 p-3 text-[13px] outline-none focus:border-violet"
        />
        <div className="flex flex-wrap gap-1.5">
          {THEMES.map((theme) => (
            <Chip
              key={theme}
              active={theme === activeTheme}
              onClick={() => onPromptChange(promptForTheme(theme))}
            >
              {theme}
            </Chip>
          ))}
          <Chip onClick={surprise}>✦ Surprise me</Chip>
        </div>

        <Label>Difficulty</Label>
        <DifficultyPicker value={difficulty} onChange={setDifficulty} />

        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1.5 rounded-xl bg-sand px-3 py-[11px] text-xs text-muted">
            Seed
            <input
              aria-label="Seed"
              inputMode="numeric"
              value={seed}
              onChange={(e) => setSeed(e.target.value.replace(/\D/g, ""))}
              placeholder="random"
              className="w-16 bg-transparent font-bold text-ink outline-none placeholder:font-normal"
            />
          </label>
          <Button type="submit" disabled={!canSubmit} className="flex-1">
            {busy ? "Starting…" : "✦  Generate world"}
          </Button>
        </div>
        {error && (
          <p role="alert" className="text-xs text-bad">
            {error}
          </p>
        )}
      </form>
    </Card>
  );
}
