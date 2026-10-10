"""[base] The world is a real planning problem: a naive baseline helps, harder levels are not easier."""

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


def _table() -> str:
    rows = [
        f"  {d:<7} baseline {_mean(d):.2f}   doing nothing {_mean(d, noop=True):.2f}"
        for d in Env.DIFFICULTIES
    ]
    return (
        "Mean score over 10 seeds:\n" + "\n".join(rows) + "\n"
        "Wanted: baseline between 0.2 and 0.9 on easy, above 0.02 and below 0.98 on every level, "
        "never better on a harder level, and better than doing nothing. "
        "A mean of 0.00 means a sensible policy never makes a profit: make revenue clearly "
        "exceed costs for it (prices, demand, costs, start cash) before anything else. "
        "Tune the score target, costs and prices in rules.py/env.py (not the tests). "
        "Higher levels must be harder for a naive player: switch on more hidden penalties, "
        "demand factors, shocks, lead times or costs with the level in rules.py, so the "
        "baseline drops by at least 0.05 from easy to hard."
    )


@pytest.fixture(params=Env.DIFFICULTIES)
def difficulty(request) -> str:
    return request.param


def test_baseline_is_neither_perfect_nor_hopeless(difficulty):
    mean = _mean(difficulty)
    assert 0.02 < mean < 0.98, f"{difficulty}: baseline mean {mean:.2f}\n{_table()}"


def test_baseline_is_a_fair_starting_point_on_easy():
    mean = _mean(Env.DIFFICULTIES[0])
    assert 0.2 <= mean <= 0.9, f"easy baseline mean {mean:.2f}\n{_table()}"


def test_doing_nothing_is_worse_than_the_baseline(difficulty):
    assert _mean(difficulty, noop=True) < _mean(difficulty), _table()


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
        assert harder <= easier + 0.05, _table()
    assert means[-1] <= means[0] - 0.05, _table()


def test_the_seed_changes_the_outcome():
    """Seeds draw values (demand, prices, parameters), so outcomes must differ between seeds."""
    for difficulty in Env.DIFFICULTIES:
        scores = {round(_final_score(difficulty, s), 4) for s in SEEDS}
        if len(scores) > 1:
            return
    pytest.fail("every seed gives the same baseline score on every level; the seed must draw values")
