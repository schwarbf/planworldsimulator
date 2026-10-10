"""[base] The server's UI state per level is dumped for the frontend contract test.

`ui/src/World.contract.test.tsx` reads these samples and checks that they have the same
shape as `mockState` in `World.tsx` and that the world view renders them. Run this
before `pixi run test-ui`.
"""

import json
from pathlib import Path

import pytest

from server.api import Game
from sim.helpers import world

SAMPLES = Path(__file__).resolve().parents[2] / "ui" / "src" / "__samples__"
DIFFICULTIES = world().DIFFICULTIES


@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_dump_state_samples(difficulty):
    game = Game(seed=5, difficulty=difficulty)
    samples = {"start": game.state()}
    game.advance(3)
    samples["week3"] = game.state()
    while not game.score()["done"]:
        game.advance(1)
    samples["end"] = game.state()
    SAMPLES.mkdir(exist_ok=True)
    for name, state in samples.items():
        (SAMPLES / f"{difficulty}-{name}.json").write_text(json.dumps(state, indent=1))
    assert samples["end"]["done"] is True
