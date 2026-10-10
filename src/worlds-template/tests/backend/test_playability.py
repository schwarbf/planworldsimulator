"""[base] The world is a real planning problem: a baseline helps, and harder levels are not easier."""

import numpy as np
import pytest

from sim.helpers import world

Env = world()
SEEDS = range(10)


def _final_score(difficulty: str, seed: int, noop: bool = False) -> float:
    env = Env(difficulty)
    env.reset(seed=seed)
    done = False
    while not done:
        action = env.encode_actions([]) if noop else env.baseline_action()
        _, _, terminated, truncated, _ = env.step(action)
        done = terminated or truncated
    return env.score()["score"]


def _mean(difficulty: str, noop: bool = False) -> float:
    return float(np.mean([_final_score(difficulty, s, noop) for s in SEEDS]))


@pytest.fixture(params=Env.DIFFICULTIES)
def difficulty(request) -> str:
    return request.param


def test_baseline_scores_strictly_between_0_and_1(difficulty):
    for seed in SEEDS:
        assert 0 < _final_score(difficulty, seed) < 1, f"{difficulty} seed {seed}"


def test_doing_nothing_is_worse_than_the_baseline(difficulty):
    assert _mean(difficulty, noop=True) < _mean(difficulty)


def test_scores_are_between_0_and_1_whatever_the_policy(difficulty):
    env = Env(difficulty)
    env.reset(seed=1)
    env.action_space.seed(1)
    done = False
    while not done:
        _, _, terminated, truncated, _ = env.step(env.action_space.sample())
        done = terminated or truncated
        assert 0 <= env.score()["score"] <= 1


def test_the_baseline_does_not_get_better_at_higher_levels():
    means = [_mean(d) for d in Env.DIFFICULTIES]
    for easier, harder in zip(means, means[1:]):
        assert harder <= easier + 0.05, f"baseline means by level: {means}"
