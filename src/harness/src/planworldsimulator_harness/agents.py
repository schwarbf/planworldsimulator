"""Load agents.toml and build a Pydantic AI model from model + base_url + key."""

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic_ai.models import Model
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.openai import OpenAIProvider

from planworldsimulator_harness.config import AGENTS_FILE


@dataclass(frozen=True)
class AgentConfig:
    name: str
    model: str
    api_key_env: str | None = None
    base_url: str | None = None
    settings: dict[str, Any] = field(default_factory=dict)
    label: str | None = None  # display name in the world UI
    color: str | None = None  # cursor colour in the world UI

    @property
    def display(self) -> str:
        return self.label or self.name


def load_agents(path: Path = AGENTS_FILE) -> dict[str, AgentConfig]:
    data = tomllib.loads(path.read_text())
    return {name: AgentConfig(name=name, **entry) for name, entry in data.items()}


def get_agent(name: str, path: Path = AGENTS_FILE) -> AgentConfig:
    agents = load_agents(path)
    if name not in agents:
        raise KeyError(f"unknown agent {name!r}; known: {', '.join(agents)}")
    return agents[name]


def api_key(name: str) -> str:
    """``$NAME``, else the contents of the file at ``$NAME_FILE`` (``~`` allowed)."""
    key = os.environ.get(name, "").strip()
    if key:
        return key
    path = os.environ.get(f"{name}_FILE", "").strip()
    if path and Path(path).expanduser().is_file():
        return Path(path).expanduser().read_text().strip()
    return ""


def build_model(cfg: AgentConfig) -> Model:
    provider, _, name = cfg.model.partition(":")
    key = api_key(cfg.api_key_env) if cfg.api_key_env else None
    if cfg.api_key_env and not key:
        raise RuntimeError(
            f"agent {cfg.name!r} needs ${cfg.api_key_env} (or ${cfg.api_key_env}_FILE)"
        )
    if provider == "google":
        return GoogleModel(
            name, provider=GoogleProvider(api_key=key, base_url=cfg.base_url)
        )
    if provider == "openai":
        return OpenAIChatModel(
            name, provider=OpenAIProvider(base_url=cfg.base_url, api_key=key)
        )
    raise ValueError(f"agent {cfg.name!r}: provider must be google or openai")
