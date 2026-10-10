"""[gen] Bike Factory invariants."""

import numpy as np
import pytest

from sim import rules as R
from sim.env import BikeFactoryEnv


@pytest.fixture(params=BikeFactoryEnv.DIFFICULTIES)
def env(request) -> BikeFactoryEnv:
    env = BikeFactoryEnv(request.param)
    env.reset(seed=3)
    env.action_space.seed(3)
    return env


class TestStockAndCash:
    def test_stock_never_negative(self, env):
        for _ in range(R.WEEKS):
            obs, *_ = env.step(env.action_space.sample())
            assert (obs["stock"] >= 0).all() and (obs["incoming"] >= 0).all()

    def test_cash_equals_start_plus_rewards(self, env):
        total = 0.0
        for _ in range(R.WEEKS):
            obs, reward, *_ = env.step(env.baseline_action())
            total += reward
        assert obs["cash"][0] == pytest.approx(R.START_CASH + total)

    def test_sold_never_exceeds_demand(self, env):
        for _ in range(10):
            obs, *_ = env.step(env.baseline_action())
            assert (obs["sold"] <= obs["demand"]).all()


class TestHiddenRules:
    def test_probe_reveals_storm_rule(self, env):
        site = R.storm_site(env.structure)
        _, _, _, _, info = env.step(env.encode_actions([("probe", {"site": site})]))
        assert any("storms" in text for text in info["discovered"])

    def test_hidden_rules_stay_out_of_the_observation(self, env):
        obs = env.observe()
        assert obs["discoveries"] == []
        assert "season" not in str(obs) and "winter" not in str(obs)

    def test_storm_delays_shipments_from_storm_site(self):
        env = BikeFactoryEnv("medium")
        env.reset(seed=5)
        env.w.storm_left = 1
        k = env.site_ids.index("tier1")
        before = [e for e in env.w.pipeline if e[1] == k]
        env.step(env.encode_actions([("order", {"site": "tier1", "qty": 10})]))
        new = [e for e in env.w.pipeline if e[1] == k and e not in before]
        assert new and all(arrive == 0 + env.params.lead[k] + R.STORM_DELAY for arrive, _, _ in new)

    def test_baseline_is_below_full_score(self):
        env = BikeFactoryEnv("medium")
        env.reset(seed=1)
        while not env.step(env.baseline_action())[2]:
            pass
        assert 0.3 < env.score()["score"] < 1.0


class TestOrders:
    """Bike-specific action checks (moved from the base tests, which are world-agnostic)."""

    def test_order_then_advance_changes_state(self):
        from server.api import Game

        game = Game(seed=4821, difficulty="medium")
        before = game.env.observe()
        assert game.act("order", {"target": "warehouse", "amount": 60})["status"] == "queued"
        game.advance(1)
        after = game.env.observe()
        assert after["week"] == before["week"] + 1
        assert after["cash"] != before["cash"]

    def test_unknown_site_is_rejected(self):
        env = BikeFactoryEnv("medium")
        env.reset(seed=1)
        with pytest.raises(ValueError):
            env.check_action("order", {"site": "nowhere", "qty": 5})
