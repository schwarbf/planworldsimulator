import { cx } from "./ui";

// A 3x3 world. The coral cells are a plan: a route from the start (bottom left)
// to the goal (top right). Same cells as public/favicon.svg.
const ROUTE = new Set(["0,2", "1,2", "1,1", "1,0", "2,0"]);
const CELL = 14;
const GAP = 3;

interface MarkProps {
  className?: string;
  /** Colour of the cells that are not part of the route. */
  base?: string;
}

export function LogoMark({ className, base = "var(--color-ink)" }: MarkProps) {
  const cells = [];
  for (let row = 0; row < 3; row++) {
    for (let col = 0; col < 3; col++) {
      const onRoute = ROUTE.has(`${col},${row}`);
      cells.push(
        <rect
          key={`${col},${row}`}
          x={col * (CELL + GAP)}
          y={row * (CELL + GAP)}
          width={CELL}
          height={CELL}
          rx={3}
          fill={onRoute ? "var(--color-coral)" : base}
        />,
      );
    }
  }
  return (
    <svg viewBox="0 0 48 48" aria-hidden className={className}>
      {cells}
    </svg>
  );
}

interface LogoProps {
  className?: string;
  /** Show only the mark on phones; the name stays available to screen readers. */
  compact?: boolean;
}

export function Logo({ className, compact }: LogoProps) {
  return (
    <span className={cx("inline-flex items-center gap-2.5", className)}>
      <LogoMark className="size-7 shrink-0" />
      <span
        className={cx(
          "font-display text-[26px] leading-none tracking-tight",
          compact && "max-sm:sr-only",
        )}
      >
        PlanWorldSimulator
      </span>
    </span>
  );
}
