"""[base] Composable multiplicative demand model. Same in every world; do not edit per world.

    demand = base × price × location × weather × time × day_of_week × events
                  × variety × competition × reputation × popularity × noise

Each factor is a function of a plain ``ctx`` dict (what the world knows this week) and
returns a multiplier; 1.0 is neutral. A factor whose inputs are missing from ``ctx``
is neutral, so a world only supplies the inputs it has. The agent never sees the
formula, only the resulting sales and demand.

A world writes ``sim/demand_config.py`` (``build(level) -> DemandModel``) from these
building blocks; factors switch on at their ``first_level`` (1 = easy … 3 = hard).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

import numpy as np

Ctx = Mapping[str, Any]
Fn = Callable[[Ctx, np.random.Generator], float]

# A factor counts as "found" once its multiplier has moved this far from neutral.
DISCOVERY_THRESHOLD = 0.08


@dataclass(frozen=True)
class Factor:
    name: str
    fn: Fn
    first_level: int = 1
    hint: str = ""  # shown as a "?" in Discoveries until the factor is found
    found: str = ""  # shown once found


@dataclass
class DemandModel:
    base: float
    factors: list[Factor] = field(default_factory=list)
    level: int = 1

    def active(self) -> list[Factor]:
        return [f for f in self.factors if f.first_level <= self.level]

    def detail(self, ctx: Ctx, rng: np.random.Generator) -> tuple[float, dict[str, float]]:
        """Demand and each active factor's multiplier (inactive factors are 1.0)."""
        mults = {f.name: _finite(f.fn(ctx, rng)) for f in self.active()}
        demand = self.base * math.prod(mults.values())
        return max(0.0, demand), mults

    def compute(self, ctx: Ctx, rng: np.random.Generator) -> float:
        return self.detail(ctx, rng)[0]

    def newly_found(self, mults: Mapping[str, float], already: set[str]) -> list[Factor]:
        return [
            f for f in self.active()
            if f.name not in already and f.found and abs(mults.get(f.name, 1.0) - 1.0) >= DISCOVERY_THRESHOLD
        ]

    def discoveries(self, found: set[str]) -> dict[str, Any]:
        """`ui_state` fragment: {total, found: [text], hidden: [hint]}."""
        active = [f for f in self.active() if f.found]
        return {
            "total": len(active),
            "found": [f.found for f in active if f.name in found],
            "hidden": [f.hint or None for f in active if f.name not in found],
        }


def _finite(x: float) -> float:
    x = float(x)
    return x if math.isfinite(x) and x >= 0 else 1.0


def _num(ctx: Ctx, key: str) -> float | None:
    v = ctx.get(key)
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


# ---------- shipped factors ----------

def price_elasticity(ref_price: float, elasticity: float = 1.2, *, first_level: int = 1, **text: str) -> Factor:
    """(price / ref_price) ** -elasticity, from ``ctx["price"]``."""
    def fn(ctx: Ctx, rng: np.random.Generator) -> float:
        price = _num(ctx, "price")
        return 1.0 if price is None or price <= 0 else (price / ref_price) ** -elasticity
    return Factor("price", fn, first_level, **text)


def affinity(weights: Mapping[str, float], *, first_level: int = 1, **text: str) -> Factor:
    """Product/audience fit: ``weights[ctx["audience"]]`` (location × audience)."""
    def fn(ctx: Ctx, rng: np.random.Generator) -> float:
        return float(weights.get(str(ctx.get("audience")), 1.0))
    return Factor("location", fn, first_level, **text)


def weather(effects: Mapping[str, float], *, first_level: int = 2, **text: str) -> Factor:
    """``effects[ctx["weather"]]``, e.g. {"rain": 0.7, "sun": 1.15}."""
    def fn(ctx: Ctx, rng: np.random.Generator) -> float:
        return float(effects.get(str(ctx.get("weather")), 1.0))
    return Factor("weather", fn, first_level, **text)


def seasonality(period: int = 52, amplitude: float = 0.2, peak: int = 0, *, first_level: int = 2, **text: str) -> Factor:
    """Sinusoid over ``ctx["week"]`` with the given period; ``peak`` is the week of the maximum."""
    def fn(ctx: Ctx, rng: np.random.Generator) -> float:
        week = _num(ctx, "week")
        return 1.0 if week is None else 1.0 + amplitude * math.cos(2 * math.pi * (week - peak) / period)
    return Factor("time", fn, first_level, **text)


def day_of_week(weights: list[float], *, first_level: int = 2, **text: str) -> Factor:
    """``weights[ctx["day"] % len(weights)]`` (e.g. 7 weights, weekend traffic)."""
    def fn(ctx: Ctx, rng: np.random.Generator) -> float:
        day = _num(ctx, "day")
        return 1.0 if day is None else float(weights[int(day) % len(weights)])
    return Factor("day_of_week", fn, first_level, **text)


def events(*, first_level: int = 3, **text: str) -> Factor:
    """Traffic multiplier of the current event (festival, market…): ``ctx["event"]``, default 1."""
    def fn(ctx: Ctx, rng: np.random.Generator) -> float:
        return _num(ctx, "event") or 1.0
    return Factor("events", fn, first_level, **text)


def variety(optimum: int, width: float = 3.0, floor: float = 0.6, *, first_level: int = 3, **text: str) -> Factor:
    """Too few or too many items hurt: Gaussian bump around ``optimum`` over ``ctx["items"]``."""
    def fn(ctx: Ctx, rng: np.random.Generator) -> float:
        n = _num(ctx, "items")
        return 1.0 if n is None else floor + (1 - floor) * math.exp(-(((n - optimum) / width) ** 2))
    return Factor("variety", fn, first_level, **text)


def competition(strength: float = 0.5, *, first_level: int = 3, **text: str) -> Factor:
    """Lose ``strength`` × competitors' share (``ctx["competitor_share"]``, 0-1) of demand."""
    def fn(ctx: Ctx, rng: np.random.Generator) -> float:
        share = _num(ctx, "competitor_share")
        return 1.0 if share is None else 1.0 - strength * min(1.0, max(0.0, share))
    return Factor("competition", fn, first_level, **text)


def reputation(weight: float = 0.05, *, first_level: int = 3, **text: str) -> Factor:
    """``1 + weight × ln(1 + reviews)`` scaled by rating (``ctx["rating"]`` 1-5, 3 = neutral)."""
    def fn(ctx: Ctx, rng: np.random.Generator) -> float:
        reviews, rating = _num(ctx, "reviews"), _num(ctx, "rating")
        if reviews is None:
            return 1.0
        stars = 1.0 if rating is None else 1.0 + 0.1 * (rating - 3.0)
        return (1.0 + weight * math.log1p(reviews)) * stars
    return Factor("reputation", fn, first_level, **text)


def popularity(*, first_level: int = 2, **text: str) -> Factor:
    """``ctx["popularity"]`` (state around 1.0); update it with ``next_popularity``."""
    def fn(ctx: Ctx, rng: np.random.Generator) -> float:
        return _num(ctx, "popularity") or 1.0
    return Factor("popularity", fn, first_level, **text)


def next_popularity(current: float, fulfilment: float, quality: float = 1.0, rate: float = 0.1) -> float:
    """Organic growth when demand is served well (fulfilment 0-1), decay when not."""
    target = 0.5 + fulfilment * quality
    return float(np.clip(current + rate * (target - current), 0.3, 2.0))


def noise(sigma: float = 0.1, *, first_level: int = 3, **text: str) -> Factor:
    """Random variance; the rng is seeded, so runs stay deterministic."""
    def fn(ctx: Ctx, rng: np.random.Generator) -> float:
        return max(0.0, float(rng.normal(1.0, sigma)))
    return Factor("noise", fn, first_level, **text)
