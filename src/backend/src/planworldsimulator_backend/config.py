from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PLANWORLDSIMULATOR_")

    database_url: str = "sqlite+aiosqlite:///./data/planworldsimulator.db"
    worlds_dir: Path = Path("src/worlds")
    template_dir: Path = Path("src/worlds-template")
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
