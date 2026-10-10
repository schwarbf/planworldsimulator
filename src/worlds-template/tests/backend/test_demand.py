"""[base] The shared demand model behaves, and this world's demand config uses it correctly."""

import json
import math

import numpy as np
import pytest

from sim import demand, demand_config
from sim.demand import DemandModel
from sim.helpers import world

Env = world()
LEVELS = range(1, len(Env.DIFFICULTIES) + 1)


@pytest.fixture(params=LEVELS)
def level(request) -> int:
    return request.param


class TestBuildingBlocks:
    def test_every_factor_is_neutral_without_inputs(self):
        rng = np.random.default_rng(0)
        factors = [
            demand.price_elasticity(10), demand.affinity({"a": 2}), demand.weather({"rain": .5}),
            demand.seasonality(), demand.day_of_week([1] * 7), demand.events(), demand.variety(5),
            demand.competition(), demand.reputation(), demand.popularity(),
        ]
        assert all(f.fn({}, rng) == 1.0 for f in factors)

    def test_factors_move_demand_the_right_way(self):
        rng = np.random.default_rng(0)
        assert demand.price_elasticity(10).fn({"price": 20}, rng) < 1 < demand.price_elasticity(10).fn({"price": 5}, rng)
        assert demand.weather({"rain": 0.6}).fn({"weather": "rain"}, rng) == 0.6
        assert demand.competition(0.5).fn({"competitor_share": 0.4}, rng) == pytest.approx(0.8)
        assert demand.variety(5).fn({"items": 5}, rng) > demand.variety(5).fn({"items": 12}, rng)
        assert demand.reputation().fn({"reviews": 100, "rating": 4.5}, rng) > 1

    def test_factor_switches_on_at_its_first_level(self):
        f = demand.weather({"rain": 0.5}, first_level=2)
        model = DemandModel(base=100, factors=[f], level=1)
        ctx, rng = {"weather": "rain"}, np.random.default_rng(0)
        assert model.compute(ctx, rng) == 100
        model.level = 2
        assert model.compute(ctx, rng) == 50

    def test_bad_factor_output_is_neutral(self):
        bad = demand.Factor("bad", lambda c, r: float("nan"))
        assert DemandModel(base=10, factors=[bad]).compute({}, np.random.default_rng(0)) == 10

    def test_popularity_grows_when_served_and_decays_when_not(self):
        assert demand.next_popularity(1.0, 1.0) > 1.0 > demand.next_popularity(1.0, 0.0)


class TestWorldConfig:
    def test_demand_is_finite_and_not_negative_over_a_rollout(self, level):
        model = demand_config.build(base=30.0, level=level)
        rng = np.random.default_rng(5)
        for week in range(60):
            value = model.compute({"week": week, "day": week}, rng)
            assert math.isfinite(value) and value >= 0

    def test_factor_names_are_unique(self, level):
        names = [f.name for f in demand_config.build(30.0, level).factors]
        assert len(names) == len(set(names))

    def test_levels_only_add_factors(self):
        counts = [len(demand_config.build(30.0, lv).active()) for lv in LEVELS]
        assert counts == sorted(counts)

    def test_hardest_level_has_more_demand_factors_than_the_easiest(self):
        counts = [len(demand_config.build(30.0, lv).active()) for lv in LEVELS]
        assert counts[-1] > counts[0]

    def test_same_seed_gives_same_demand(self, level):
        def run():
            model, rng = demand_config.build(30.0, level), np.random.default_rng(9)
            return [model.compute({"week": w}, rng) for w in range(20)]
        assert run() == run()

    def test_discoveries_add_up_and_are_json(self, level):
        model = demand_config.build(30.0, level)
        info = model.discoveries({f.name for f in model.active()[:1]})
        assert info["total"] == len(info["found"]) + len(info["hidden"])
        json.dumps(info)
