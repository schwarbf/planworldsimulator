"""[gen] TODO: replace with this world's invariants. Reference: src/worlds/bike-factory/tests/backend/test_rules.py"""

import pytest

from sim.env import ExampleEnv


@pytest.fixture(params=ExampleEnv.DIFFICULTIES)
def env(request) -> ExampleEnv:
    env = ExampleEnv(request.param)
    env.reset(seed=3)
    return env


class TestInvariants:
    def test_capacity_never_negative(self, env):
        for _ in range(12):
            obs, *_ = env.step(env.baseline_action())
            assert obs["capacity"][0] >= 0

    def test_invalid_amount_is_rejected(self, env):
        with pytest.raises(ValueError):
            env.check_action("invest", {"amount": 99})
