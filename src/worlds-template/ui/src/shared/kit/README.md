# SVG kit

Isometric building blocks for `World.tsx`. Every component returns an SVG `<g>`;
`x, y` is always the screen point where the object stands (its ground centre).
See `src/World.tsx` (Bike Factory) for a full example.

## Rules

- **Painter's order:** draw objects sorted by `i + j` ascending (back to front).
  Ground (island, path/water tiles, rings, flows, moving vehicles) goes first.
- Put the `<svg>` inside `<Stage width height overlay>`; place `Hud` pills in
  `overlay` with `toPercent(x, y, width, height)` so they line up with the SVG.
- Colours are hex strings; faces are shaded automatically.
- **Agent cursor:** give each actionable object its id as `target` (on `Hud` and/or
  `Building`; rendered as `data-target="map:<id>"`). When the agent acts with an
  argument equal to that id (e.g. `order(site="warehouse")`), the cursor moves there.

## iso.ts

- `makeGrid({ cx, cy, n, size, slab = 16 })` → `grid` with `at(i, j)` (tile centre
  on top of the slab), `diamond(i, j, k = 1)` (tile corners, scaled by `k` for
  rings), `uv(i, j)` and the projector `p(u, v, z)`.
- `project(cx, cy)` → `(u, v, z = 0) => [cx + (u − v), cy + (u + v)/2 − z]`.
- `shade(hex, f)` darker for `f < 1`, lighter toward white for `f > 1`.
- `pts(points)` → SVG `points` string. `toPercent(x, y, w, h)` → `{ x, y }` in %.
- `useSvgId(prefix)` → unique id for `<filter>` / `url(#…)`.

## Components

| Component | Props | Notes |
| --- | --- | --- |
| `Stage` | `width, height, overlay?` | Frame for the SVG + HTML overlay at a fixed aspect ratio. |
| `IsoIsland` | `grid, tileKind?(i, j)` | Floating slab with tiles; kinds `grass`, `path`, `water`, `none`. Children draw on top. |
| `IsoBox` | `x, y, w, d, h, color, top?, z0?, stroke?` | `w` along down-right, `d` along down-left. Left face = color, right 0.8, top 1.3. |
| `Building` | `x, y, w, d, h, color, roof?, gable?, chimney?, windows? = true, z0?, target?` | Windows on both faces; `roof` colour = flat roof box, with `gable` = gable roof. `buildingTop(props)` = drawn height (for Hud placement). |
| `Tree` | `x, y, color?, scale?` | Round crown. |
| `Person` | `x, y, color?, skin?, scale?` | Worker with yellow hard hat. |
| `Vehicle` | `x, y, kind = truck \| car \| ship, color?, dir = u \| v, reverse?, scale?` | Animate by wrapping it at `0,0` in a `<g>` with `<animateMotion path=…>`. |
| `Fog` | `x, y, size, question?` | Raised grey tile over unexplored ground. |
| `Cloud` | `x, y, scale?, color?, opacity?` | Soft blurred cloud (exported from `Weather` and `Fog`). |
| `Sun` / `Storm` | `x, y, r?` / `x, y, scale?` | Storm = grey clouds + flashing bolt. |
| `Flow` | `points, color = white, width = 3, animated = true` | Glow + dashed line; animated dashes run from first to last point. |

Use CSS class `pulse` on any element to make it blink (alerts), and `clickable`
on a `<g>` for a pointer cursor.
