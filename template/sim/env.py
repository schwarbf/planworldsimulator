"""[gen] Bike Factory: a Gymnasium env for a bike supply chain. One step = one week.

Difficulty fixes the structure (sites, actions, hidden rules); the seed only
draws values (lead times, demand, hidden-rule parameters).
"""

from __future__ import annotations

from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from sim import rules as R
from sim.helpers import obs_to_json, register_world

BIG = 1e9


class BikeFactoryEnv(gym.Env):
    NAME = "Bike Factory"
    DIFFICULTIES = ("easy", "medium", "hard")
    metadata = {"render_modes": []}

    def __init__(self, difficulty: str = "medium"):
        if difficulty not in self.DIFFICULTIES:
            raise ValueError(f"difficulty must be one of {self.DIFFICULTIES}")
        self.difficulty = difficulty
        self.structure = R.STRUCTURES[difficulty]
        self.site_ids: list[str] = list(self.structure.sites)
        self.actions: tuple[str, ...] = self.structure.actions
        n = len(self.site_ids)

        act: dict[str, spaces.Space] = {"order": spaces.MultiDiscrete([R.MAX_ORDER + 1] * n), "probe": spaces.MultiBinary(n)}
        if "expand" in self.actions:
            act["expand"] = spaces.MultiBinary(n)
        self.action_space = spaces.Dict(act)

        vec = spaces.Box(0, BIG, shape=(n,), dtype=np.float64)
        self.observation_space = spaces.Dict({
            "week": spaces.Discrete(R.WEEKS + 1),
            "cash": spaces.Box(-BIG, BIG, shape=(1,), dtype=np.float64),
            "storm": spaces.Discrete(2),
            "stock": vec, "incoming": vec, "backlog": vec, "capacity": vec, "lead": vec, "level": vec,
            "demand": vec, "sold": vec, "shipped": vec,
        })
        self.params: R.Params | None = None
        self.w: R.WorldState | None = None

    # ---------- Gymnasium API ----------

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        self.params = R.draw_params(self.np_random, self.structure)
        self.w = R.initial_state(self.np_random, self.structure, self.params)
        return self._obs(), self._info()

    def step(self, action: dict[str, np.ndarray]):
        assert self.w is not None and self.params is not None, "call reset() first"
        n = len(self.site_ids)
        order = np.clip(np.asarray(action["order"], dtype=np.int64), 0, R.MAX_ORDER)
        expand = np.asarray(action.get("expand", np.zeros(n)), dtype=np.int8)
        probe = np.asarray(action["probe"], dtype=np.int8)
        res = R.step_world(self.np_random, self.structure, self.params, self.w, order, expand, probe)
        terminated = self.w.t >= R.WEEKS
        info = self._info() | {"reward": res.reward, "discovered": res.discovered, "story": res.story}
        return self._obs(), float(res.reward), terminated, False, info

    def _obs(self) -> dict[str, Any]:
        w = self.w
        assert w is not None and self.params is not None
        n = len(self.site_ids)
        incoming = np.zeros(n)
        for _, k, qty in w.pipeline:
            incoming[k] += qty
        backlog = np.array([sum(q for _, q in reqs) for reqs in w.requests], dtype=np.float64)
        f = lambda a: np.array(a, dtype=np.float64)  # copies  # noqa: E731
        return {
            "week": int(w.t),
            "cash": f([w.cash]),
            "storm": int(w.storm_left > 0),
            "stock": f(w.stock), "incoming": incoming, "backlog": backlog, "capacity": f(w.capacity),
            "lead": f(self.params.lead), "level": f(w.level),
            "demand": f(w.demand), "sold": f(w.sold), "shipped": f(w.shipped),
        }

    def _info(self) -> dict[str, Any]:
        w = self.w
        assert w is not None
        return {"week": w.t, "cash": w.cash, "profit": w.cash - R.START_CASH, "served": self._served()}

    def _served(self) -> float:
        w = self.w
        assert w is not None
        return 1.0 if w.demand_total == 0 else w.sold_total / w.demand_total

    # ---------- world contract used by server/api.py ----------

    def check_action(self, verb: str, args: dict[str, Any]) -> dict[str, Any]:
        """Validate one player action; returns normalised args or raises ValueError."""
        if verb not in self.actions:
            raise ValueError(f"'{verb}' is not available here; actions: {', '.join(self.actions)}")
        site = args.get("site") or args.get("target") or "warehouse"
        if site not in self.site_ids:
            raise ValueError(f"unknown site '{site}'; sites: {', '.join(self.site_ids)}")
        if verb == "order":
            qty = args.get("qty", args.get("amount"))
            if not isinstance(qty, (int, float)) or qty <= 0 or qty > R.MAX_ORDER:
                raise ValueError(f"order needs qty between 1 and {R.MAX_ORDER}")
            return {"site": site, "qty": int(qty)}
        if verb == "expand" and R.SITES[site][1] == "store":
            raise ValueError("stores cannot be expanded")
        return {"site": site}

    def encode_actions(self, queued: list[tuple[str, dict[str, Any]]]) -> dict[str, np.ndarray]:
        """Merge the week's queued actions into one Gymnasium action."""
        n = len(self.site_ids)
        action = {k: np.zeros(n, dtype=np.int64 if k == "order" else np.int8) for k in self.action_space.spaces}
        for verb, args in queued:
            k = self.site_ids.index(args["site"])
            if verb == "order":
                action["order"][k] = min(R.MAX_ORDER, action["order"][k] + args["qty"])
            else:
                action[verb][k] = 1
        return action

    def baseline_action(self) -> dict[str, np.ndarray]:
        """Naive policy for the baseline score: every site re-orders last week's outflow."""
        w = self.w
        assert w is not None
        out = w.demand + w.requested
        return self.encode_actions([("order", {"site": sid, "qty": int(out[k])}) for k, sid in enumerate(self.site_ids) if out[k] > 0])

    def observe(self, site: str | None = None) -> dict[str, Any]:
        """Visible observation as JSON (hidden rules stay out)."""
        data = obs_to_json(self._obs(), self.site_ids)
        data["week"] = data["week"] + 1 if self.w and self.w.t < R.WEEKS else R.WEEKS
        data["weeks"] = R.WEEKS
        for sid, v in data["sites"].items():
            v["name"], v["type"] = R.SITES[sid][0], R.SITES[sid][1]
            v["upstream"] = self.structure.upstream.get(sid, "raw market")
        data["discoveries"] = list(self.w.discovered) if self.w else []
        if site is not None:
            if site not in self.site_ids:
                raise ValueError(f"unknown site '{site}'; sites: {', '.join(self.site_ids)}")
            return {"week": data["week"], "storm": data["storm"], "site": site, **data["sites"][site]}
        return data

    def score(self) -> dict[str, Any]:
        """Score in [0, 1]: 60% profit vs target, 40% customers served vs 95%."""
        w = self.w
        assert w is not None
        profit, served = w.cash - R.START_CASH, self._served()
        target = self.structure.target
        value = 0.6 * float(np.clip(profit / target, 0, 1)) + 0.4 * min(1.0, served / R.SERVED_TARGET)
        return {"score": round(value, 4), "profit": round(profit), "target": target, "served": round(served, 4),
                "week": min(w.t + 1, R.WEEKS), "done": w.t >= R.WEEKS}

    def ui_state(self, ctx: dict[str, Any]) -> dict[str, Any]:
        """State for ui/src/World.tsx (same shape as its mockState)."""
        w, p, s = self.w, self.params, self.structure
        assert w is not None and p is not None
        obs = self._obs()
        sites = []
        for k, sid in enumerate(self.site_ids):
            name, kind, i, j = R.SITES[sid]
            if kind == "store":
                pct = min(1.0, w.stock[k] / max(1.0, 2 * (w.demand[k] or p.base_demand[k])))
                backlog = w.demand[k] - w.sold[k]
            else:
                pct = min(1.0, w.shipped[k] / w.capacity[k]) if w.capacity[k] else 0.0
                backlog = obs["backlog"][k]
            sites.append({
                "id": sid, "name": name, "type": kind, "i": i, "j": j,
                "level": int(w.level[k]), "pct": round(float(pct), 3),
                "stock": int(w.stock[k]), "incoming": int(obs["incoming"][k]), "leadWeeks": int(p.lead[k]),
                "backlog": int(backlog), "holdingPerWeek": int(round(w.stock[k] * w.hold[k])),
                "outOfStock": bool(kind == "store" and w.stock[k] == 0 and w.t > 0),
            })
        found = list(w.discovered)
        hidden = [R.rule_hint(r) if r in w.hinted else None for r in s.rules if R.rule_text(s, p, r) not in found]
        fog = [(i, j, (i, j) in {(8, 0), (10, 1), (0, 1)}) for i in range(11) for j in range(11)
               if (len(found) < 1 and i >= 7 and j <= 1) or (len(found) < len(s.rules) and i <= 1 and j <= 2)]
        storm = None
        if w.storm_left > 0:
            _, _, si, sj = R.SITES[R.storm_site(s)]
            storm = [max(0, si - 1), min(10, sj + 1)]
        sc = self.score()
        return {
            "world": {"name": self.NAME, "seed": str(ctx.get("seed", "")), "difficulty": self.difficulty.title()},
            "cash": int(round(w.cash)),
            "perDay": int(round(w.last_reward / 7)),
            "week": min(w.t + 1, R.WEEKS),
            "weeks": R.WEEKS,
            "sites": sites,
            "routes": [{"from": up, "to": sid} for sid, up in s.upstream.items() if sid in self.site_ids],
            "fog": fog,
            "water": [[5, 7], [6, 7], [5, 8], [6, 8]],
            "trees": [[0, 4], [0, 7], [1, 10], [3, 1], [4, 1], [6, 0], [6, 10], [10, 9], [10, 10], [3, 7], [10, 3]],
            "workers": [[3, 4], [6, 4]],
            "storm": storm,
            "story": ctx.get("story"),
            "discoveries": {"total": len(s.rules), "found": found, "hidden": hidden},
            "goal": {"profit": sc["profit"], "target": s.target, "served": sc["served"], "servedTarget": R.SERVED_TARGET},
            "agent": ctx.get("agent", {}),
            "dock": {"active": ctx.get("active") or "order", "unlocked": len(self.actions), "total": 8},
            "queued": ctx.get("queued", []),
            "done": w.t >= R.WEEKS,
        }


register_world(BikeFactoryEnv)
