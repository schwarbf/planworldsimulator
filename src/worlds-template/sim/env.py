"""[gen] TODO: replace with this world's Gymnasium env (contract: README.md).

Placeholder world so the template runs: one shop, invest to grow capacity,
sell to a demand drawn from the seed. One step = one week.
Reference implementation: src/worlds/bike-factory/sim/env.py
"""

from __future__ import annotations

from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from sim import rules as R
from sim.helpers import calibrated_target, obs_to_json, register_world


class ExampleEnv(gym.Env):
    NAME = "Example world"
    DIFFICULTIES = ("easy", "medium", "hard")
    metadata = {"render_modes": []}

    def __init__(self, difficulty: str = "medium"):
        if difficulty not in self.DIFFICULTIES:
            raise ValueError(f"difficulty must be one of {self.DIFFICULTIES}")
        self.difficulty = difficulty
        self.actions: tuple[str, ...] = ("invest",)  # world verbs = MCP action tools
        self.site_ids = ["shop"]
        # Difficulty fixes the structure and the spaces.
        self.action_space = spaces.Dict({"invest": spaces.Discrete(R.MAX_INVEST + 1)})
        self.observation_space = spaces.Dict({
            "week": spaces.Discrete(R.WEEKS + 1),
            "cash": spaces.Box(-R.BIG, R.BIG, shape=(1,), dtype=np.float64),
            "capacity": spaces.Box(0, R.BIG, shape=(1,), dtype=np.float64),
            "demand": spaces.Box(0, R.BIG, shape=(1,), dtype=np.float64),
        })
        self.w: R.WorldState | None = None

    # ---------- Gymnasium API ----------

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        self.w = R.initial_state(self.np_random, self.DIFFICULTIES.index(self.difficulty) + 1)  # seed only draws values
        return self._obs(), {}

    def step(self, action: dict[str, Any]):
        assert self.w is not None, "call reset() first"
        reward = R.step_world(self.np_random, self.w, int(action["invest"]))
        discovered = [f.found for f in self.w.new_found]
        return self._obs(), float(reward), self.w.week >= R.WEEKS, False, {"discovered": discovered, "story": None}

    def _obs(self) -> dict[str, Any]:
        w = self.w
        assert w is not None
        f = lambda v: np.array([v], dtype=np.float64)  # noqa: E731
        return {"week": int(w.week), "cash": f(w.cash), "capacity": f(w.capacity), "demand": f(w.demand)}

    # ---------- world contract used by server/api.py ----------

    def check_action(self, verb: str, args: dict[str, Any]) -> dict[str, Any]:
        if verb not in self.actions:
            raise ValueError(f"'{verb}' is not available; actions: {', '.join(self.actions)}")
        amount = args.get("amount", 1)
        if not isinstance(amount, int) or not 1 <= amount <= R.MAX_INVEST:
            raise ValueError(f"invest needs amount between 1 and {R.MAX_INVEST}")
        return {"amount": amount}

    def encode_actions(self, queued: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
        return {"invest": min(R.MAX_INVEST, sum(a["amount"] for _, a in queued))}

    def baseline_action(self) -> dict[str, Any]:
        return {"invest": 1}

    def observe(self, site: str | None = None) -> dict[str, Any]:
        return obs_to_json(self._obs(), self.site_ids)

    def result(self) -> float:
        """Raw outcome (here profit); ``score()`` is this divided by the calibrated target."""
        assert self.w is not None
        return self.w.cash - R.START_CASH

    def target(self) -> float:
        """The profit that scores 1.0; derived from the baseline, never hand-tuned."""
        return calibrated_target(type(self))

    def score(self) -> dict[str, Any]:
        w = self.w
        assert w is not None
        profit = w.cash - R.START_CASH
        return {"score": round(float(np.clip(profit / self.target(), 0, 1)), 4), "profit": round(profit),
                "week": min(w.week + 1, R.WEEKS), "done": w.week >= R.WEEKS, "formula": f"profit vs CHF {self.target():,.0f}"}

    def ui_state(self, ctx: dict[str, Any]) -> dict[str, Any]:
        """Same shape as `mockState` in ui/src/World.tsx."""
        w = self.w
        assert w is not None
        sc = self.score()
        return {
            "world": {"name": self.NAME, "seed": str(ctx.get("seed", "")), "difficulty": self.difficulty.title()},
            "week": sc["week"],
            "weeks": R.WEEKS,
            "cash": int(w.cash),
            "capacity": int(w.capacity),
            "demand": int(w.demand),
            "profit": sc["profit"],
            "target": round(self.target()),
            "story": ctx.get("story"),
            "discoveries": w.model.discoveries(w.found),
            "agent": ctx.get("agent", {}),
            "active": ctx.get("active"),
            "queued": ctx.get("queued", []),
            "done": sc["done"],
        }


register_world(ExampleEnv)
