"""[base] Gymnasium contract and determinism for every difficulty."""

import numpy as np
import pytest
from gymnasium.utils.env_checker import check_env

from sim.helpers import world

Env = world()


def _rollout(difficulty: str, seed: int, steps: int = 20) -> list:
    env = Env(difficulty)
    env.reset(seed=seed)
    env.action_space.seed(seed)
    trace = []
    for _ in range(steps):
        obs, reward, terminated, truncated, _ = env.step(env.action_space.sample())
        trace.append((obs, reward))
        if terminated or truncated:
            break
    return trace


@pytest.fixture(params=Env.DIFFICULTIES)
def difficulty(request) -> str:
    return request.param


class TestGymnasiumContract:
    def test_check_env(self, difficulty):
        check_env(Env(difficulty), skip_render_check=True)

    def test_episode_terminates(self, difficulty):
        env = Env(difficulty)
        env.reset(seed=0)
        for _ in range(1000):
            *_, terminated, truncated, _ = env.step(env.baseline_action())
            if terminated or truncated:
                return
        pytest.fail("episode did not end")


class TestDeterminism:
    def test_same_seed_and_actions_give_same_trace(self, difficulty):
        a, b = _rollout(difficulty, 7), _rollout(difficulty, 7)
        for (oa, ra), (ob, rb) in zip(a, b, strict=True):
            assert ra == rb
            for key in oa:
                np.testing.assert_array_equal(oa[key], ob[key])

    def test_other_seed_changes_values_not_structure(self, difficulty):
        e1, e2 = Env(difficulty), Env(difficulty)
        o1, _ = e1.reset(seed=1)
        o2, _ = e2.reset(seed=2)
        assert e1.observation_space == e2.observation_space
        assert e1.action_space == e2.action_space
        # The seed must draw values (demand, prices, lead times, positions...): the
        # first observation or the first weeks of the baseline policy must differ.
        trace1, trace2 = [o1], [o2]
        for _ in range(6):
            trace1.append(e1.step(e1.baseline_action())[0])
            trace2.append(e2.step(e2.baseline_action())[0])
        differs = any(
            not np.array_equal(a[k], b[k]) for a, b in zip(trace1, trace2) for k in a
        )
        assert differs, (
            f"seeds 1 and 2 give identical observations on {difficulty} for the first "
            "weeks. Draw values from self.np_random (the seeded generator that "
            "reset(seed=...) sets up) in reset()/initial_state(), for example the base "
            "demand, prices or starting stock, and put them into the observation."
        )
