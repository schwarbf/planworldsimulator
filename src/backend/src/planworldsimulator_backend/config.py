from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PLANWORLDSIMULATOR_")

    database_url: str = "sqlite+aiosqlite:///./data/planworldsimulator.db"
    worlds_dir: Path = Path("src/worlds")
    template_dir: Path = Path("src/worlds-template")
    # fake: walks through the steps without an LLM; opencode: the real coding agent.
    generator: str = "fake"
    gemini_api_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "GEMINI_API_KEY", "PLANWORLDSIMULATOR_GEMINI_API_KEY"
        ),
    )
    generator_model: str = "google/gemini-3.5-flash"  # 3.8 is about 6x slower
    generator_variant: str = "minimal"  # OpenCode reasoning effort; low = faster
    opencode_bin: str = "opencode"
    # Hard cap for one world, all steps together.
    generation_deadline_seconds: float = 300
    fix_rounds: int = 5  # also bounded by the deadline
    max_tool_calls: int = 60
    # Interpreter for world servers and tests; default: the template's pixi env.
    world_python: Path | None = None
    # Example world the agent may read; copied into `reference/` and removed at the end.
    reference_dir: Path | None = Path("src/worlds/bike-factory")
    # fake: hands out ports only; process: runs each world's server. auto follows
    # `generator` (a real generator needs real servers).
    launcher: str = "auto"
    # Pause between fake generation steps, so progress is visible in the UI.
    step_delay_seconds: float = 1.0
    # Public use: anyone can generate and play, so keep it bounded.
    create_limit_per_hour: int = 5
    max_generating: int = 3
    max_running: int = 10
    idle_stop_seconds: int = 1800
    reap_interval_seconds: float = 60
    seed_featured: bool = True
    # Only trust X-Forwarded-For when a proxy you control sets it (nginx does).
    trust_forwarded_for: bool = False
    cookie_secure: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
