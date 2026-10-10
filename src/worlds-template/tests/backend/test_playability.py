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
        "Wanted: baseline between 0.2 and 0.9 on easy, above 0.02 on medium, below 0.98 on every "
        "level, never better on a harder level, and better than doing nothing on easy. "
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
    """Hard may defeat the naive baseline (an expert mode); easy and medium may not."""
    mean = _mean(difficulty)
    floor = 0.0 if difficulty == Env.DIFFICULTIES[-1] else 0.02
    assert floor <= mean < 0.98, f"{difficulty}: baseline mean {mean:.2f}\n{_table()}"


def test_baseline_is_a_fair_starting_point_on_easy():
    mean = _mean(Env.DIFFICULTIES[0])
    assert 0.2 <= mean <= 0.9, f"easy baseline mean {mean:.2f}\n{_table()}"


def test_doing_nothing_is_not_better_than_the_baseline(difficulty):
    assert _mean(difficulty, noop=True) <= _mean(difficulty), _table()


def test_doing_nothing_is_worse_than_the_baseline_on_easy():
    easy = Env.DIFFICULTIES[0]
    baseline, nothing = _mean(easy), _mean(easy, noop=True)
    if abs(baseline - nothing) < 1e-6:
        why = (
            f"Doing nothing and the baseline score exactly the same ({baseline:.2f}): the "
            "baseline's actions have no effect on the result, or baseline_action() is the "
            "same as the empty action. Make baseline_action() return a real action that "
            "raises the result, and make sure every action changes the world in "
            "rules.py (an action that is stored but never used there does nothing)."
        )
    else:
        why = f"The baseline ({baseline:.2f}) must beat doing nothing ({nothing:.2f})."
    assert nothing < baseline, f"{why}\n{_table()}"


def test_actions_change_the_outcome(difficulty):
    """Random actions must lead somewhere other than doing nothing, or actions are dead."""
    env = Env(difficulty)
    differing = 0
    for seed in range(5):
        env.reset(seed=seed)
        env.action_space.seed(seed)
        done = False
        while not done:
            _, _, terminated, truncated, _ = env.step(env.action_space.sample())
            done = terminated or truncated
        random_result = env.result()
        env.reset(seed=seed)
        done = False
        while not done:
            _, _, terminated, truncated, _ = env.step(env.encode_actions([]))
            done = terminated or truncated
        differing += abs(random_result - env.result()) > 1e-9
    assert differing, (
        f"On {difficulty}, random actions give exactly the same result as doing nothing "
        "on every seed: the actions have no effect. Use every action's arguments in "
        "rules.py so that it changes costs, capacity, demand or stock."
    )


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
