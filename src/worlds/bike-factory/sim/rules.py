"""[gen] Bike Factory dynamics and hidden rules.

One step = one week. Goods flow Tier 2 → Tier 1 → Components → Assembly →
Warehouse → Stores (1 part = 1 component = 1 bike). Ordering at a site asks
its upstream site to ship; the top supplier buys from the raw-parts market.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

WEEKS = 52
START_CASH = 100_000.0
PRICE = 450.0  # per bike sold at a store
RAW_COST = 150.0  # per part bought by the top supplier
SHIP_COST = 4.0  # per unit shipped between sites
PROBE_COST = 500.0
MAX_ORDER = 500
SERVED_TARGET = 0.95
STORM_DELAY = 2  # extra weeks on shipments from the storm site
HOLD_RATE = {"supplier": 1.5, "plant": 3.0, "assembly": 5.0, "warehouse": 5.0, "store": 6.0}


def expand_cost(site_type: str) -> float:
    return 12_000.0 if site_type == "warehouse" else 8_000.0


# ---------- structure (fixed per difficulty) ----------

# id: (name, type, tile i, tile j)
SITES: dict[str, tuple[str, str, int, int]] = {
    "tier2": ("Tier 2 Supplier", "supplier", 1, 8),
    "tier1": ("Tier 1 Supplier", "supplier", 4, 10),
    "components": ("Components", "plant", 2, 5),
    "assembly": ("Assembly", "assembly", 5, 3),
    "warehouse": ("Warehouse", "warehouse", 7, 6),
    "storeA": ("Store A", "store", 9, 2),
    "storeB": ("Store B", "store", 10, 6),
    "storeC": ("Store C", "store", 8, 9),
}


@dataclass(frozen=True)
class Structure:
    sites: tuple[str, ...]
    upstream: dict[str, str]  # site → the site it orders from (top supplier: none)
    actions: tuple[str, ...]
    rules: tuple[str, ...]  # hidden rules in this difficulty
    target: float  # profit goal
    overhead: float  # fixed cost per week
    storm_bonus: float = 0.0


_CHAIN = {"tier1": "tier2", "components": "tier1", "assembly": "components", "warehouse": "assembly",
          "storeA": "warehouse", "storeB": "warehouse", "storeC": "warehouse"}

STRUCTURES: dict[str, Structure] = {
    "easy": Structure(
        sites=("tier1", "assembly", "warehouse", "storeA", "storeB"),
        upstream={"assembly": "tier1", "warehouse": "assembly", "storeA": "warehouse", "storeB": "warehouse"},
        actions=("order", "probe"),
        rules=("seasonality", "storms"),
        target=800_000.0,
        overhead=2_500.0,
    ),
    "medium": Structure(
        sites=tuple(SITES),
        upstream=_CHAIN,
        actions=("order", "expand", "probe"),
        rules=("seasonality", "storms", "winter"),
        target=1_000_000.0,
        overhead=4_000.0,
    ),
    "hard": Structure(
        sites=tuple(SITES),
        upstream=_CHAIN,
        actions=("order", "expand", "probe"),
        rules=("seasonality", "storms", "winter", "competitor"),
        target=1_000_000.0,
        overhead=5_000.0,
        storm_bonus=0.05,
    ),
}


# ---------- values (drawn per seed) ----------


@dataclass
class Params:
    lead: np.ndarray  # weeks for shipments into each site
    base_demand: np.ndarray  # mean weekly demand per site (0 for non-stores)
    season_period: int
    season_amp: float
    season_phase: int
    storm_p: float
    winter_mult: float
    competitor_start: int
    competitor_share: float


def draw_params(rng: np.random.Generator, s: Structure) -> Params:
    lead = np.zeros(len(s.sites), dtype=np.int64)
    base = np.zeros(len(s.sites))
    for k, sid in enumerate(s.sites):
        kind = SITES[sid][1]
        if sid not in s.upstream:
            lead[k] = rng.integers(3, 6)  # raw market → top supplier
        elif kind == "supplier":
            lead[k] = rng.integers(2, 4)
        elif kind == "warehouse":
            lead[k] = rng.integers(1, 3)
        else:
            lead[k] = 1
        if kind == "store":
            base[k] = float(rng.integers(18, 33))
    period = int(rng.integers(7, 10))
    return Params(
        lead=lead,
        base_demand=base,
        season_period=period,
        season_amp=float(rng.uniform(0.3, 0.45)),
        season_phase=int(rng.integers(0, period)),
        storm_p=float(rng.uniform(0.12, 0.2)) + s.storm_bonus,
        winter_mult=float(rng.uniform(1.6, 2.2)),
        competitor_start=int(rng.integers(10, 26)),
        competitor_share=float(rng.uniform(0.2, 0.35)),
    )


def is_winter(t: int) -> bool:
    week = t + 1
    return week <= 9 or week >= 48


def demand_mean(s: Structure, p: Params, k: int, t: int) -> float:
    """Expected demand at site k in week t, including the hidden rules."""
    sid = s.sites[k]
    mean = p.base_demand[k]
    if mean == 0:
        return 0.0
    if "seasonality" in s.rules:
        mean *= 1 + p.season_amp * np.sin(2 * np.pi * (t + p.season_phase) / p.season_period)
    if "winter" in s.rules and sid == "storeB" and is_winter(t):
        mean *= p.winter_mult
    if "competitor" in s.rules and sid == "storeC" and t >= p.competitor_start:
        mean *= 1 - p.competitor_share
    return float(mean)


# ---------- hidden rules: where they live, what they reveal ----------


def storm_site(s: Structure) -> str:
    return next(sid for sid in s.sites if sid not in s.upstream)


def rule_site(s: Structure, rule: str) -> tuple[str, ...]:
    """Sites where probing reveals the rule."""
    return {
        "seasonality": tuple(sid for sid in s.sites if SITES[sid][1] == "store"),
        "storms": (storm_site(s),),
        "winter": ("storeB",),
        "competitor": ("storeC",),
    }[rule]


def rule_text(s: Structure, p: Params, rule: str) -> str:
    return {
        "seasonality": f"Store demand peaks every ~{p.season_period} weeks",
        "storms": f"{SITES[storm_site(s)][0].removesuffix(' Supplier')} is late after storms (+{STORM_DELAY} wk)",
        "winter": f"Store B sells ×{p.winter_mult:.1f} in winter",
        "competitor": f"A competitor near Store C takes {round(p.competitor_share * 100)}% of its customers",
    }[rule]


def rule_hint(rule: str) -> str:
    return {
        "seasonality": "Store demand moves in waves",
        "storms": "Deliveries feel slower after storms",
        "winter": "Store B behaves oddly in winter",
        "competitor": "Store C is losing customers",
    }[rule]


# ---------- dynamic state ----------


@dataclass
class WorldState:
    t: int
    cash: float
    stock: np.ndarray
    capacity: np.ndarray
    hold: np.ndarray
    level: np.ndarray
    pipeline: list[tuple[int, int, int]]  # (arrival week, site, qty)
    requests: list[list[list[int]]]  # per upstream site: FIFO of [downstream site, qty]
    storm_left: int = 0
    demand: np.ndarray = field(default_factory=lambda: np.zeros(0))
    sold: np.ndarray = field(default_factory=lambda: np.zeros(0))
    shipped: np.ndarray = field(default_factory=lambda: np.zeros(0))
    requested: np.ndarray = field(default_factory=lambda: np.zeros(0))
    demand_total: float = 0.0
    sold_total: float = 0.0
    last_reward: float = 0.0
    discovered: list[str] = field(default_factory=list)
    hinted: set[str] = field(default_factory=set)
    storms_seen: int = 0


def initial_state(rng: np.random.Generator, s: Structure, p: Params) -> WorldState:
    n = len(s.sites)
    flow = float(p.base_demand.sum())
    stock = np.zeros(n)
    capacity = np.zeros(n)
    hold = np.zeros(n)
    pipeline: list[tuple[int, int, int]] = []
    for k, sid in enumerate(s.sites):
        kind = SITES[sid][1]
        hold[k] = HOLD_RATE[kind]
        if kind == "store":
            stock[k] = round(1.5 * p.base_demand[k])
            per_week = p.base_demand[k]
        else:
            stock[k] = round(flow * rng.uniform(0.6, 1.0))
            factor = rng.uniform(1.0, 1.15) if kind == "assembly" else rng.uniform(1.3, 1.6)
            capacity[k] = round(flow * factor)
            per_week = flow
        for w in range(int(p.lead[k])):
            pipeline.append((w, k, int(round(per_week))))
    zeros = np.zeros(n)
    return WorldState(
        t=0, cash=START_CASH, stock=stock, capacity=capacity, hold=hold, level=np.ones(n, dtype=np.float64) * 2,
        pipeline=pipeline, requests=[[] for _ in range(n)],
        demand=zeros.copy(), sold=zeros.copy(), shipped=zeros.copy(), requested=zeros.copy(),
    )


@dataclass
class StepResult:
    reward: float
    discovered: list[str]
    story: dict | None


def step_world(
    rng: np.random.Generator, s: Structure, p: Params, w: WorldState,
    order: np.ndarray, expand: np.ndarray, probe: np.ndarray,
) -> StepResult:
    n = len(s.sites)
    idx = {sid: k for k, sid in enumerate(s.sites)}
    cash_before = w.cash
    discovered: list[str] = []
    probed_nothing: list[str] = []

    # 1. Expand and probe.
    for k, sid in enumerate(s.sites):
        kind = SITES[sid][1]
        if expand[k] and kind != "store":
            w.cash -= expand_cost(kind)
            w.capacity[k] = round(w.capacity[k] * 1.2)
            w.hold[k] *= 1.08
            w.level[k] += 1
        if probe[k]:
            w.cash -= PROBE_COST
            found = next((r for r in s.rules if sid in rule_site(s, r) and rule_text(s, p, r) not in w.discovered), None)
            if found:
                text = rule_text(s, p, found)
                w.discovered.append(text)
                discovered.append(text)
            else:
                probed_nothing.append(SITES[sid][0])

    # 2. Orders: the top supplier buys raw parts, everyone else asks upstream.
    w.requested = np.zeros(n)
    for k, sid in enumerate(s.sites):
        qty = int(order[k])
        if qty <= 0:
            continue
        up = s.upstream.get(sid)
        if up is None:
            w.cash -= qty * RAW_COST
            w.pipeline.append((w.t + int(p.lead[k]), k, qty))
        else:
            w.requests[idx[up]].append([k, qty])
            w.requested[idx[up]] += qty

    # 3. Arrivals.
    for arrive, k, qty in w.pipeline:
        if arrive <= w.t:
            w.stock[k] += qty
    w.pipeline = [e for e in w.pipeline if e[0] > w.t]

    # 4. Shipping, limited by stock and capacity, first come first served.
    stormy = w.storm_left > 0
    w.shipped = np.zeros(n)
    for u in range(n):
        avail = min(w.stock[u], w.capacity[u])
        for req in w.requests[u]:
            if avail <= 0:
                break
            d, qty = req
            ship = int(min(avail, qty))
            if ship <= 0:
                continue
            avail -= ship
            w.stock[u] -= ship
            w.shipped[u] += ship
            req[1] -= ship
            delay = STORM_DELAY if stormy and s.sites[u] == storm_site(s) else 0
            w.pipeline.append((w.t + int(p.lead[d]) + delay, d, ship))
            w.cash -= ship * SHIP_COST
        w.requests[u] = [r for r in w.requests[u] if r[1] > 0]

    # 5. Customers at the stores; unmet demand is lost.
    w.demand = np.zeros(n)
    w.sold = np.zeros(n)
    for k in range(n):
        mean = demand_mean(s, p, k, w.t)
        if mean <= 0:
            continue
        d = float(rng.poisson(mean))
        sold = min(d, w.stock[k])
        w.stock[k] -= sold
        w.demand[k], w.sold[k] = d, sold
        w.cash += sold * PRICE
    w.demand_total += float(w.demand.sum())
    w.sold_total += float(w.sold.sum())

    # 6. Holding and overhead.
    w.cash -= float((w.stock * w.hold).sum()) + s.overhead

    # 7. Weather for next week.
    storm_started = False
    if w.storm_left > 0:
        w.storm_left -= 1
    elif "storms" in s.rules and rng.random() < p.storm_p:
        w.storm_left = int(rng.integers(1, 3))
        w.storms_seen += 1
        storm_started = True

    # 8. Hints: a rule shows a vague hint once its effect has happened.
    week = w.t + 1
    if week >= p.season_period:
        w.hinted.add("seasonality")
    if w.storms_seen:
        w.hinted.add("storms")
    if is_winter(w.t) and w.t >= 2:
        w.hinted.add("winter")
    if w.t >= p.competitor_start + 2:
        w.hinted.add("competitor")

    w.t += 1
    w.last_reward = w.cash - cash_before

    story = None
    out = [s.sites[k] for k in range(n) if w.demand[k] > w.sold[k]]
    if discovered:
        story = {"tag": "FOUND", "text": discovered[0], "tone": "mint"}
    elif storm_started:
        name = SITES[storm_site(s)][0].removesuffix(" Supplier")
        story = {"tag": f"WEEK {week}", "text": f"Storms reported near {name}. Deliveries feel slower…", "tone": "amber"}
    elif out:
        story = {"tag": f"WEEK {week}", "text": f"{SITES[out[0]][0]} ran out of stock — customers left.", "tone": "coral"}
    elif probed_nothing:
        story = {"tag": f"WEEK {week}", "text": f"Probe at {probed_nothing[0]}: nothing unusual.", "tone": "mint"}
    return StepResult(reward=w.last_reward, discovered=discovered, story=story)
