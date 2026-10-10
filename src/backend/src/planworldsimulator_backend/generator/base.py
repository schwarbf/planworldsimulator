from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

STEPS = (
    "check_exists",
    "copy_template",
    "design",
    "sim",
    "ui",
    "tests",
    "polish",
    "smoke",
    "publish",
)
# Every generated world ships with all of these; the level is chosen when playing.
LEVELS = (1, 2, 3)  # website level N is the template's DIFFICULTIES[N - 1]


@dataclass(frozen=True)
class GenerationEvent:
    step: str
    state: str  # started | done | exists | trace (one line of the live log)
    message: str = ""
    storyline: str | None = None
    path: str | None = None
    duplicate_of: str | None = None  # with state "exists": the world that has the name
    elapsed_seconds: float = 0
    metrics: dict | None = None  # with state "trace": {"trace": kind}


@dataclass(frozen=True)
class GenerationRequest:
    world_id: str
    title: str
    prompt: str
    seed: int
    attempt: int = 1
    model: str = ""  # generator.models id; "" = the configured default


class Generator(Protocol):
    def run(self, request: GenerationRequest) -> AsyncIterator[GenerationEvent]: ...
