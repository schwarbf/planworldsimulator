import type { ControlsModel } from "../types";

/** Logo, product name and "World #seed · name · difficulty". */
export function Brand({ brand }: { brand: ControlsModel["brand"] }) {
  return (
    <div className="brand">
      <div className="brand__logo">
        <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden>
          <path d="M8 1l7 7-7 7-7-7z" fill="var(--coral)" />
        </svg>
      </div>
      <div>
        <div className="brand__name">PlanWorldSimulator</div>
        <div className="muted">
          World #{brand.seed} · {brand.world} · {brand.difficulty}
        </div>
      </div>
    </div>
  );
}
