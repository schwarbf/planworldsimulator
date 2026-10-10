# Example world

<!-- [gen] TODO: public brief, given to the agent. Reference: src/worlds/bike-factory/brief.md -->

## Story

You run a small shop for 12 weeks.

## Goal

Make as much profit as you can. Your score (0 to 1) is your profit relative to a target, which `score()` reports.

## Actions

- `invest(amount)` — add capacity (CHF 50 per unit), applied on the next `advance`.
- `advance(weeks)` — simulate time.
