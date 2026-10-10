"""[gen] TODO: replace with this world's dynamics and hidden rules (see secret.md).

Reference implementation: src/worlds/bike-factory/sim/rules.py
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sim import demand_config
from sim.demand import DemandModel, Factor

WEEKS = 12
MAX_INVEST = 10
START_CASH = 1000.0
TARGET = 3500.0
BIG = 1e9
PRICE, INVEST_COST = 10.0, 50.0


@dataclass
class WorldState:
    week: int
    cash: float
    capacity: float
    demand: float
    model: DemandModel
    found: set[str]  # demand factors whose effect has been seen
    new_found: list[Factor]  # found in the last step


def initial_state(rng: np.random.Generator, level: int) -> WorldState:
    """``level`` is 1 (easy) … 3 (hard); the seed only draws values (here: the base demand)."""
    model = demand_config.build(base=float(rng.integers(20, 40)), level=level)
    demand, _ = model.detail({"week": 0}, rng)
    return WorldState(0, START_CASH, 10.0, demand, model, set(), [])


def step_world(rng: np.random.Generator, w: WorldState, invest: int) -> float:
    """Advance one week; returns the week's profit."""
    w.capacity += 2 * invest
    sold = min(w.demand, w.capacity)
    profit = sold * PRICE - invest * INVEST_COST
    w.cash += profit
    w.week += 1
    w.demand, mults = w.model.detail({"week": w.week}, rng)
    w.new_found = w.model.newly_found(mults, w.found)
    w.found |= {f.name for f in w.new_found}
    return profit
