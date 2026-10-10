import { LEVEL_NAMES, playUrl, type World } from "../api/client";

/** One link per difficulty level. Opening one starts the world on demand. */
export function PlayLevels({ world }: { world: World }) {
  return (
    <div
      role="group"
      aria-label={`Play ${world.title}`}
      className="flex flex-wrap items-center gap-2"
    >
      <span className="mr-1 font-mono text-xs text-muted uppercase">
        Play at
      </span>
      {world.levels.map((level) => (
        <a
          key={level}
          href={playUrl(world.id, level)}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`Play ${world.title} at level ${level}`}
          className="rounded-md border border-ink px-3 py-1.5 text-sm font-semibold transition-colors hover:bg-ink hover:text-white"
        >
          {LEVEL_NAMES[level - 1] ?? `L${level}`}
        </a>
      ))}
    </div>
  );
}
