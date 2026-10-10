"""[base] Hidden rules stay hidden: nothing from secret.md reaches the agent or the UI."""

import json
import re
from pathlib import Path

import pytest

from server.api import Game
from sim.helpers import world

ROOT = Path(__file__).resolve().parents[2]
Env = world()


def _terms(secret: str, brief: str) -> set[str]:
    """Backticked names in secret.md's hidden-rules part (before "## Scoring") that brief.md lacks."""
    terms = {t.lower() for t in re.findall(r"`([^`]{4,})`", secret.split("## Scoring")[0])}
    return {t for t in terms if t not in brief.lower()}


def _secret_terms() -> set[str]:
    return _terms((ROOT / "secret.md").read_text(), (ROOT / "brief.md").read_text())


def test_term_extraction():
    secret = "## Hidden rules\n- `rain_penalty` halves sales; `stock` is public\n## Scoring\n- `score`"
    assert _terms(secret, "Watch your stock.") == {"rain_penalty"}


@pytest.fixture(params=Env.DIFFICULTIES)
def game(request) -> Game:
    return Game(seed=11, difficulty=request.param)


def test_secret_terms_are_not_in_the_brief():
    brief = (ROOT / "brief.md").read_text().lower()
    assert not [t for t in _secret_terms() if t in brief]


def test_secret_terms_never_reach_observations_or_state(game):
    terms = _secret_terms()
    done = False
    while not done:
        seen = json.dumps([game.observe(), game.state(), game.score()]).lower()
        leaked = [t for t in terms if t in seen]
        assert not leaked, f"leaked: {leaked}"
        done = game.advance(1)["done"]


def test_hidden_demand_rules_start_hidden(game):
    """Before anything happens no factor text is revealed in the UI state."""
    assert game.state()["discoveries"]["found"] == []
