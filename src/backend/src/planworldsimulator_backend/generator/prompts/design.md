You are the game designer for PlanWorld, a benchmark of planning worlds. An AI agent will later play the world through tool calls; a human plays it through a website. Design ONE world from this request.

World name: $title
Request: $description
Seed for inspiration only: $seed

Write exactly one file, `design.md`, in a single `write` call. Do not read or run anything else; everything you need is below. Be concrete and short (at most 130 lines). Use these sections, with exactly these `##` headings:

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
The goal in one sentence, the score formula (0 to 1) and the naive baseline policy. The baseline must score about 0.4 to 0.6 on Easy and do worse on Hard.

## UI state
The JSON that the server returns at `/api/state` and the web view reads, as one JSON example in a ```json block. Start from the base fields below and add the fields the view needs (per-site stats, resources, targets). Keep it flat and small. All numbers must be plain numbers.
Base fields (keep them exactly): `world {name, seed (string), difficulty (string)}`, `week`, `weeks`, `story {tag, text, tone: "amber"|"mint"|"coral"} | null`, `discoveries {total, found: string[], hidden: (string|null)[]}`, `agent {experiment, experiments, mode: "you"|"agent", scores: number[], baseline, now, code}`, `active: string | null`, `done: boolean`.

## Visual concept
For the isometric web view: palette (4 to 5 hex colours with roles), island grid size (6 to 8 tiles), where each site stands (tile i,j), what objects sit around it (buildings, trees, people, vehicles, weather, flows) and what is animated. At least 8 objects in total.

Available isometric kit (names only): Stage, IsoIsland, IsoBox, Building, Tree, Person, Vehicle (truck, car, ship), Fog, Cloud, Sun, Storm, Flow.

Template contract, for reference:

$readme
