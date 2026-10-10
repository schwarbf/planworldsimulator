You are the art director for a PlanWorld world. The attached screenshots show the world "$title" at levels 1, 2 and 3 (easy, medium, hard), as a player sees it. Judge only the isometric world in the middle of the page (the island and what stands on it); the panels around it are shared and fixed.

Check it against this list:

$checklist

First look at the screenshots. If the world already meets the list, change nothing and reply "ok". Otherwise fix the most visible problems (overlapping labels, empty corners, too few objects, objects hidden behind others, flat colours, nothing moving) by rewriting `ui/src/World.tsx` completely with ONE `write` call, in the same turn. Keep the exports `State`, `mockState`, `toControls` and `WorldView` and their types unchanged, keep the state keys unchanged, and keep to the design below. Do not read or run anything else.

## Design (palette, island, objects)

$visual

## Kit documentation

$kit_readme

## Current `ui/src/World.tsx`

$world
