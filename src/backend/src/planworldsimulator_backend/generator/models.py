"""Models the world generator can use; the website lets the creator pick one.

Slower models get proportionally more time: their time limit is the configured
`generation_deadline_seconds` times `time_factor`.
"""

from dataclasses import dataclass

from planworldsimulator_backend.config import Settings


@dataclass(frozen=True)
class GeneratorModel:
    id: str
    label: str
    opencode: str  # OpenCode `--model`
    variant: str  # OpenCode `--variant` (reasoning effort)
    time_factor: float
    note: str


MODELS: dict[str, GeneratorModel] = {
    m.id: m
    for m in (
        GeneratorModel(
            "gemini-3.5-flash",
            "Gemini 3.5 Flash",
            "google/gemini-3.5-flash",
            "minimal",
            1,
            "fast",
        ),
        GeneratorModel(
            "gemini-3.8-flash",
            "Gemini 3.8 Flash",
            "google/gemini-3.8-flash",
            "minimal",
            3,
            "newest Flash, slower",
        ),
        GeneratorModel(
            "gemini-3.1-pro-preview",
            "Gemini 3.1 Pro",
            "google/gemini-3.1-pro-preview",
            "low",
            4,
            "strongest, slowest",
        ),
        GeneratorModel(
            "gemini-3.5-flash-lite",
            "Gemini 3.5 Flash-Lite",
            "google/gemini-3.5-flash-lite",
            "minimal",
            1,
            "fastest",
        ),
    )
}
DEFAULT_MODEL = "gemini-3.5-flash"


@dataclass(frozen=True)
class Resolved:
    """What one generation actually runs with."""

    opencode: str
    variant: str
    deadline_seconds: float


def resolve(model_id: str | None, settings: Settings) -> Resolved:
    """A known model id, or the configured default (`generator_model`) otherwise."""
    model = MODELS.get(model_id or "")
    if model is None:
        return Resolved(
            settings.generator_model,
            settings.generator_variant,
            settings.generation_deadline_seconds,
        )
    return Resolved(
        model.opencode,
        model.variant,
        settings.generation_deadline_seconds * model.time_factor,
    )
