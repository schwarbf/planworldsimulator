You are the game designer for PlanWorld, a benchmark of planning worlds. An AI agent will later play the world through tool calls; a human plays it through a website. Design ONE world from this request.

World name: $title
Request: $description
Seed for inspiration only: $seed

Write exactly one file, `design.json`, in a single `write` call. Do not read or run anything else. Produce JSON matching the schema below. Call `write` with BOTH arguments: `filePath: "$design_path"` and `content: "<the complete JSON as a string>"`. Never omit filePath. The pipeline validates it and derives design.md, the TypeScript State type, and mockState. Those derived files are read-only.

## JSON schema
$spec_schema

## Base state fields
These are supplied by the pipeline; state_fields describes ONLY additional world fields.
$base_state

Include a complete state_sample matching base fields plus state_fields. All object properties are required; nullable fields accept null. Arrays require an explicit items type even if the sample array is empty. Declare enum values for world-specific categorical strings when needed. state_sample.weeks must equal weeks. Each action argument includes its primitive type and explicit limits. levels must contain easy, medium, hard, with site/action IDs and rules. Each site has a tile [i,j] within the visual grid. Keep descriptions concise.

Follow this design guidance, encoded into the corresponding JSON fields:

## Storyline
3 to 5 sentences: who the player is, what they run, what the goal is and what makes it hard. Plain text, no markdown.

## Sites
2 to 4 sites in total (places or entities the player manages), each as `id` — what it is. Level 1 uses the first 2, level 3 uses all.

## Actions
At most 5 verbs, each as `verb(arg: type)` with one line of meaning and its limits. One time step = one week; the episode is 12 to 16 weeks.

## Hidden rules
Exactly 3 hidden rules that a clever agent can discover by experimenting (not by reading the brief). For each: the rule with numbers, and how experimenting reveals it. They interact on the hard level.

## Demand
Which of these shipped demand factors the world uses and with what parameters, and the first level (1, 2 or 3) that switches each on: price_elasticity, affinity, weather, seasonality, day_of_week, events, variety, competition, reputation, popularity, noise. Use 4 to 7 factors; noise and at least two others only at level 3. Each factor needs a one-line `hint` ("?" shown to the player) and a `found` text.

## Levels
A table with rows Easy (level 1), Medium (level 2), Hard (level 3) and the columns sites, actions, hidden rules active, demand factors active, other changes (lead times, shocks, fog). Hard is an expert mode: many interacting factors, delayed effects, the agent sees only sales and demand, never the formula.

## Scoring
The goal in one sentence, what the raw result is (for example profit) and the naive baseline policy (one sensible action repeated every week). The score is calibrated automatically so the baseline scores about 0.5 on Easy; the baseline must do clearly worse on Hard.

## UI state
The JSON that the server returns at `/api/state` and the web view reads, as one JSON example in a ```json block. Start from the base fields below and add the fields the view needs (per-site stats, resources, targets). Keep it flat and small. All numbers must be plain numbers.
Base fields (keep them exactly): `world {name, seed (string), difficulty (string)}`, `week`, `weeks`, `story {tag, text, tone: "amber"|"mint"|"coral"} | null`, `discoveries {total, found: string[], hidden: (string|null)[]}`, `agent {experiment, experiments, mode: "you"|"agent", scores: number[], baseline, now, code}`, `active: string | null`, `done: boolean`.

## Visual concept
For the isometric web view: palette (4 to 5 hex colours with roles), island grid size (6 to 8 tiles), where each site stands (tile i,j), what objects sit around it (buildings, trees, people, vehicles, weather, flows) and what is animated. At least 8 objects in total.

Available isometric kit (names only): Stage, IsoIsland, IsoBox, Building, Tree, Person, Vehicle (truck, car, ship), Fog, Cloud, Sun, Storm, Flow.

Template contract, for reference:

$readme
