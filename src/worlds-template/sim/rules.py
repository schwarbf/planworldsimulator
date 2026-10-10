"""[gen] TODO: replace with this world's dynamics and hidden rules (see secret.md).

Reference implementation: src/worlds/bike-factory/sim/rules.py
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

WEEKS = 12
MAX_INVEST = 10
START_CASH = 1000.0
TARGET = 2000.0
BIG = 1e9
PRICE, INVEST_COST = 10.0, 50.0


@dataclass
class WorldState:
    week: int
    cash: float
    capacity: float
    demand: float


def initial_state(rng: np.random.Generator, difficulty: str) -> WorldState:
    return WorldState(week=0, cash=START_CASH, capacity=10.0, demand=float(rng.integers(20, 40)))


def step_world(rng: np.random.Generator, w: WorldState, invest: int) -> float:
    """Advance one week; returns the week's profit."""
    w.capacity += 2 * invest
    sold = min(w.demand, w.capacity)
    profit = sold * PRICE - invest * INVEST_COST
    w.cash += profit
    w.demand = max(0.0, w.demand + float(rng.normal(0, 3)))
    w.week += 1
    return profit
