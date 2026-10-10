"""[base] Observation → JSON and world registration. Same in every world; do not edit per world."""

from __future__ import annotations

from typing import Any

import gymnasium as gym
import numpy as np

_world: type[gym.Env] | None = None


def register_world(env_cls: type[gym.Env]) -> type[gym.Env]:
    """Register the world's env with Gymnasium (``PlanWorld/<Class>-v0``) and as this server's world."""
    global _world
    _world = env_cls
    env_id = f"PlanWorld/{env_cls.__name__.removesuffix('Env')}-v0"
    if env_id not in gym.registry:
        gym.register(id=env_id, entry_point=env_cls)
    return env_cls


def world() -> type[gym.Env]:
    """The env class registered by ``sim/env.py``."""
    if _world is None:
        import sim.env  # noqa: F401  (registers on import)
    assert _world is not None, "sim/env.py must call register_world(EnvClass)"
    return _world


_targets: dict[type, float] = {}


def calibrated_target(env_cls: type[gym.Env], baseline_share: float = 0.5, seeds: int = 5) -> float:
    """The result that scores 1.0: the naive baseline's mean ``result()`` on the easiest level
    is ``baseline_share`` of it, so the baseline scores about 0.5 on easy by construction.

    Never hand-tune a score target: call this from ``score()``. ``env_cls`` needs
    ``DIFFICULTIES``, ``baseline_action()`` and ``result()`` (the raw outcome, e.g. profit).
    """
    if env_cls not in _targets:
        results = []
        for seed in range(seeds):
            env = env_cls(env_cls.DIFFICULTIES[0])  # type: ignore[attr-defined]
            env.reset(seed=seed)
            done = False
            while not done:
                _, _, terminated, truncated, _ = env.step(env.baseline_action())  # type: ignore[attr-defined]
                done = terminated or truncated
            results.append(env.result())  # type: ignore[attr-defined]
        mean = sum(results) / len(results)
        # A baseline that never earns anything cannot define a scale; score 0 then shows it.
        _targets[env_cls] = mean / baseline_share if mean > 0 else 1.0
    return _targets[env_cls]


def difficulty_for_level(level: Any) -> str:
    """Website level 1, 2, 3 → the env's difficulty name (``DIFFICULTIES[level - 1]``)."""
    difficulties = world().DIFFICULTIES  # type: ignore[attr-defined]
    if not isinstance(level, int) or isinstance(level, bool) or not 1 <= level <= len(difficulties):
        raise ValueError(f"level must be an integer from 1 to {len(difficulties)}")
    return difficulties[level - 1]


def to_jsonable(x: Any) -> Any:
    """Recursively turn numpy arrays/scalars (and tuples) into plain JSON values."""
    if isinstance(x, dict):
        return {str(k): to_jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [to_jsonable(v) for v in x]
    if isinstance(x, np.ndarray):
        return to_jsonable(x.tolist())
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.floating):
        v = float(x)
        return int(v) if v.is_integer() else round(v, 4)
    if isinstance(x, float):
        return int(x) if x.is_integer() else round(x, 4)
    return x


def obs_to_json(obs: dict[str, Any], site_ids: list[str]) -> dict[str, Any]:
    """Dict observation → ``{..., "sites": {id: {key: value}}}``.

    Arrays with one entry per site become per-site fields; everything else
    stays top level (length-1 arrays are unwrapped).
    """
    out: dict[str, Any] = {}
    sites: dict[str, dict[str, Any]] = {sid: {} for sid in site_ids}
    for key, value in obs.items():
        arr = np.asarray(value)
        if arr.ndim == 1 and len(arr) == len(site_ids):
            for sid, v in zip(site_ids, arr):
                sites[sid][key] = to_jsonable(v)
        elif arr.ndim == 1 and len(arr) == 1:
            out[key] = to_jsonable(arr[0])
        else:
            out[key] = to_jsonable(value)
    out["sites"] = sites
    return out
