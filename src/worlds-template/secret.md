# Example world — secret

<!-- [gen] TODO: hidden rules and scoring; never given to the agent. Reference: src/worlds/bike-factory/secret.md -->

## Hidden rules

- None in the placeholder.

## Scoring

- Score = profit / target, clipped to 0–1, where the target is calibrated so the naive baseline scores about 0.5 on easy (`calibrated_target`).
- Baseline: invest 1 every week.
