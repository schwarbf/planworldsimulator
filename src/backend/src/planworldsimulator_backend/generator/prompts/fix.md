The quality gates failed for this world. Fix the problems in YOUR files only ($files). The gates are the spec: never edit tests other than `tests/backend/test_rules.py`, and never edit anything under `tests/backend` that is not yours.

$failures

First read, in ONE turn and in parallel, every failing test file named above and your files that the failures point at, so you understand what is checked. Then write the corrected files completely, in as few turns as possible. Fix the root cause (for example: use the seed to draw values, tune constants so the scores land in the wanted range), not the symptom. Keep `design.md` and the contract. $extra
