import { cx } from "./ui";

const LEVELS = [
  { value: 1, name: "Easy", dots: "bg-good" },
  { value: 2, name: "Medium", dots: "bg-amber" },
  { value: 3, name: "Hard", dots: "bg-coral" },
  { value: 4, name: "Expert", dots: "bg-violet" },
];

const TABLE: [string, string[]][] = [
  ["Sites", ["3", "8", "12", "20"]],
  ["Hidden rules", ["1", "3", "5", "8"]],
  ["Shocks", ["none", "rare", "frequent", "chained"]],
  ["Demand", ["steady", "seasonal", "+ trend", "regime shifts"]],
  ["Lead times", ["fixed", "± 1 wk", "± 3 wk", "random + fails"]],
  ["Visibility", ["full map", "fog of war", "+ delayed data", "+ lost sales"]],
  ["Goal", ["profit", "+ service", "+ cash cap", "multi-objective"]],
];

interface Props {
  value: number;
  onChange: (value: number) => void;
}

export function DifficultyPicker({ value, onChange }: Props) {
  return (
    <div className="flex flex-col gap-3">
      <div
        role="radiogroup"
        aria-label="Difficulty"
        className="flex gap-1 rounded-[14px] bg-sand p-1"
      >
        {LEVELS.map((level) => {
          const active = level.value === value;
          return (
            <button
              key={level.value}
              type="button"
              role="radio"
              aria-checked={active}
              onClick={() => onChange(level.value)}
              className={cx(
                "flex flex-1 flex-col items-center gap-1 rounded-chip py-2 text-xs font-semibold",
                active ? "bg-white text-ink shadow-pop" : "text-muted",
              )}
            >
              <span className="flex gap-[3px]" aria-hidden>
                {LEVELS.map((dot) => (
                  <span
                    key={dot.value}
                    className={cx(
                      "size-1.5 rounded-full",
                      dot.value <= level.value ? level.dots : "bg-line",
                    )}
                  />
                ))}
              </span>
              {level.name}
            </button>
          );
        })}
      </div>
      <div className="overflow-hidden rounded-[14px] border border-line text-[11px]">
        {TABLE.map(([name, cells], row) => (
          <div
            key={name}
            className={cx(
              "grid grid-cols-[88px_repeat(4,1fr)]",
              row % 2 === 1 && "bg-sand-2",
            )}
          >
            <span className="px-2.5 py-[9px] font-semibold text-muted">
              {name}
            </span>
            {cells.map((cell, col) => (
              <span
                key={cell}
                className={cx(
                  "px-2.5 py-[9px]",
                  col + 1 === value && "bg-highlight font-bold",
                )}
              >
                {cell}
              </span>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
