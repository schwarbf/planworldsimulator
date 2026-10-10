from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

STEPS = (
    "check_exists",
    "copy_template",
    "design",
    "fill",
    "tests",
    "smoke",
    "publish",
)
# Every generated world ships with all of these; the level is chosen when playing.
LEVELS = (1, 2, 3)  # website level N is the template's DIFFICULTIES[N - 1]


@dataclass(frozen=True)
class GenerationEvent:
    step: str
    state: str  # started | done | exists
    message: str = ""
    storyline: str | None = None
    path: str | None = None
    duplicate_of: str | None = None  # with state "exists": the world that has the name


@dataclass(frozen=True)
class GenerationRequest:
    world_id: str
    title: str
    prompt: str
    seed: int


class Generator(Protocol):
    def run(self, request: GenerationRequest) -> AsyncIterator[GenerationEvent]: ...
