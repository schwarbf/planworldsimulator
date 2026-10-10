# Bike Factory — secret rules (never shown to the agent)

## Hidden rules

| Rule | Difficulty | Effect | Revealed by |
|---|---|---|---|
| Seasonality | all | Store demand × (1 + A·sin(2π(t+φ)/P)); P = 7–9 weeks (peaks every ~8 weeks), A = 0.30–0.45. | probe any store |
| Storms | all | Each week a storm starts with p = 0.12–0.20 (Hard +0.05) and lasts 1–2 weeks; shipments from Tier 2 (Easy: Tier 1) take +2 weeks. | probe Tier 2 (Easy: Tier 1) |
| Store B winter | Medium, Hard | Store B demand × 1.6–2.2 in weeks 1–9 and 48–52. | probe Store B |
| Competitor | Hard | From week 10–25 on, Store C loses 20–35% of its customers. | probe Store C |

A vague hint appears in the UI once a rule's effect has happened.

## Values drawn per seed

Lead times (top supplier 3–5 wk, other suppliers 2–3, warehouse 1–2, others 1),
base store demand (18–32 / week), capacities (Assembly 1.0–1.15× mean flow is
the bottleneck), starting stock, and the rule parameters above.

## Scoring

`score = 0.6 · clip(profit / target, 0, 1) + 0.4 · min(1, served / 0.95)`,
target CHF 1M (Easy 800k). Baseline = every site re-orders last week's outflow.
