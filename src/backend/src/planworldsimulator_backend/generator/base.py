from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

# The fake generator walks through the first four; the real one through all of them.
STEPS = (
    "check_exists",
    "design",
    "copy_template",
    "fill",
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
