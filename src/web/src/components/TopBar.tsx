import { Link } from "react-router";

export function TopBar() {
  return (
    <header className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-5">
      <Link to="/" className="flex items-center gap-3">
        <span className="grid size-10 place-items-center rounded-xl bg-ink">
          <span className="size-4 rotate-45 rounded-[3px] bg-coral" />
        </span>
        <span>
          <span className="block font-display text-base leading-tight font-bold">
            PlanBench
          </span>
          <span className="block text-xs text-muted">
            Agentic planning arena
          </span>
        </span>
      </Link>
    </header>
  );
}
