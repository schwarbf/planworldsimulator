"""[gen] TODO: replace with this world's demand factors (see sim/demand.py for the blocks).

Pick the factors that fit the story, give them parameters, and set the first level
that switches each on. Reference implementation: src/worlds/bike-factory/sim/.
`hint` is the "?" shown in Discoveries; `found` is shown once the factor's effect has
been seen (a multiplier at least 8% away from 1.0).
"""

from __future__ import annotations

from sim import demand
from sim.demand import DemandModel


def build(base: float, level: int) -> DemandModel:
    """``level`` is 1 (easy) … 3 (hard)."""
    return DemandModel(
        base=base,
        level=level,
        factors=[
            demand.seasonality(
                period=4, amplitude=0.25, first_level=2,
                hint="Demand seems to move in a cycle.", found="Demand follows a 4-week cycle.",
            ),
            demand.noise(sigma=0.12, first_level=3),
        ],
    )
